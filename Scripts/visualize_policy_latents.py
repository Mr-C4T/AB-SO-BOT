#!/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Run a policy on a dataset or a real robot and stream its internal latent tokens as a 3D
point cloud in Rerun, next to the camera feeds.

How it works
------------
Every LeRobot policy is a plain ``torch.nn.Module`` wrapping an internal ``model`` (an
``ACT``/``VAE`` transformer, a diffusion U-Net, a VLM + action-expert, ...). Rather than special
-casing each architecture, this script attaches a single ``torch.nn.Module.register_forward_hook``
to a submodule you name on the CLI (``--hook_module``, dotted attribute path, default
``model.encoder`` which is right for ACT) and captures whatever tensor that submodule outputs on
every policy call. The output is reshaped to ``(num_tokens, hidden_dim)``, and once enough frames
have been observed a *frozen* 3-component PCA is fit once and reused every step afterwards -- so
the point cloud stays spatially coherent across time instead of being re-projected (and rotating/
flipping) on every single frame. Each token is colored by its index, which is stable across time
for a given architecture, so you can visually track e.g. "the CLS/latent token" vs. "camera-patch
tokens" moving around the embedding space as the episode plays out.

Good ``--hook_module`` values to try:
    ACT policies:        model.encoder                 (S, B, D) transformer tokens
    Diffusion policies:  model.rgb_encoder / model.unet
    SmolVLA:              model.vlm_with_expert         VLM hidden states
    pi0 / pi0.5 / pi0_fast: model.paligemma_with_expert
Run ``python -c "from lerobot.policies... import ...Policy; print(...Policy)"`` or just
``print(policy)`` after loading (this script does that at startup with ``--list_modules=true``)
to see all named submodules for your specific checkpoint.

Requires the ``viz`` extra: ``pip install 'lerobot[viz]'``

Usage examples
--------------
Run on a dataset episode:
::
    python examples/latent_pointcloud/visualize_policy_latents.py \\
        --source=dataset \\
        --policy.path=lerobot/act_aloha_sim_transfer_cube_human \\
        --dataset_repo_id=lerobot/aloha_sim_transfer_cube_human \\
        --episode=0 \\
        --hook_module=model.encoder

Run on a real robot:
::
    python examples/latent_pointcloud/visualize_policy_latents.py \\
        --source=robot \\
        --policy.path=lerobot/act_koch_real \\
        --robot.type=koch_follower \\
        --robot.port=/dev/ttyACM0 \\
        --task="pick up the cube" \\
        --hook_module=model.encoder

List a checkpoint's named submodules without running anything (to pick --hook_module):
::
    python examples/latent_pointcloud/visualize_policy_latents.py \\
        --policy.path=lerobot/act_koch_real --list_modules=true
"""

import colorsys
import logging
import time
from dataclasses import dataclass, field

import numpy as np
import torch
from torch import Tensor, nn

from lerobot.cameras.opencv import OpenCVCameraConfig  # noqa: F401
from lerobot.cameras.realsense import RealSenseCameraConfig  # noqa: F401
from lerobot.configs import PreTrainedConfig, parser
from lerobot.datasets import LeRobotDataset, LeRobotDatasetMetadata, resolve_delta_timestamps
from lerobot.policies import get_policy_class, make_pre_post_processors
from lerobot.policies.utils import build_inference_frame, make_robot_action
from lerobot.robots import (  # noqa: F401
    Robot,
    RobotConfig,
    koch_follower,
    make_robot_from_config,
    so_follower,
)
from lerobot.utils.hub import HubMixin
from lerobot.utils.rerun_visualization import init_rerun, log_rerun_data, shutdown_rerun
from lerobot.utils.utils import init_logging

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------------------------


@dataclass
class LatentVizConfig(HubMixin):
    """Configuration for the latent point-cloud visualization script."""

    # Policy to load. Pass --policy.path=<hub_id_or_local_dir>.
    policy: PreTrainedConfig | None = None

    # "dataset" replays a dataset episode through the policy; "robot" runs a live control loop.
    source: str = "dataset"

    # --- dataset source ---
    dataset_repo_id: str | None = None
    episode: int = 0

    # --- robot source ---
    robot: RobotConfig | None = None
    task: str = ""
    fps: int = 30

    # Dotted attribute path (from the policy's `.model`) to hook for latent tokens.
    hook_module: str = "model.encoder"
    # Print every named submodule of the loaded policy and exit, instead of running.
    list_modules: bool = False

    # Number of policy calls to buffer before fitting the frozen 3D PCA projection.
    warmup_frames: int = 30
    max_steps: int = 1000

    device: str | None = None

    # Rerun connection (leave both None to spawn a local viewer).
    display_ip: str | None = None
    display_port: int | None = None

    def __post_init__(self) -> None:
        policy_path = parser.get_path_arg("policy")
        if policy_path:
            cli_overrides = parser.get_cli_overrides("policy")
            self.policy = PreTrainedConfig.from_pretrained(policy_path, cli_overrides=cli_overrides)
            self.policy.pretrained_path = policy_path
        elif self.policy is None:
            raise ValueError("A policy is required, please provide --policy.path")

        if not self.list_modules:
            if self.source == "dataset" and not self.dataset_repo_id:
                raise ValueError("--dataset_repo_id is required when --source=dataset")
            if self.source == "robot" and self.robot is None:
                raise ValueError("--robot.type is required when --source=robot")
            if self.source not in ("dataset", "robot"):
                raise ValueError(f"--source must be 'dataset' or 'robot', got {self.source!r}")

        if self.device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"

    @classmethod
    def __get_path_fields__(cls) -> list[str]:
        """Enables --policy.path=local/dir or --policy.path=hub/id."""
        return ["policy"]


# --------------------------------------------------------------------------------------------
# Latent-token extraction and projection
# --------------------------------------------------------------------------------------------


def resolve_module(root: nn.Module, dotted_path: str) -> nn.Module:
    """Walks a dotted attribute path (e.g. "model.encoder") starting from `root`."""
    module = root
    for attr in dotted_path.split("."):
        if not hasattr(module, attr):
            raise AttributeError(
                f"{module.__class__.__name__} has no submodule '{attr}' (from --hook_module="
                f"'{dotted_path}'). Re-run with --list_modules=true to see valid options."
            )
        module = getattr(module, attr)
    return module


def extract_tokens(hook_output) -> Tensor:
    """Normalizes a captured forward-hook output into a (num_tokens, hidden_dim) tensor.

    Assumes batch_size == 1, which holds for both the dataset loop (one frame at a time) and the
    real-robot control loop (one frame per tick) in this script. Handles the common shapes seen
    across LeRobot policies: (S, 1, D) / (1, S, D) transformer tokens, (1, D) pooled vectors, and
    (1, C, H, W)-style conv feature maps (flattened to one "token" per spatial location).
    """
    tensor = hook_output
    if isinstance(tensor, (tuple, list)):
        tensor = tensor[0]
    if not torch.is_tensor(tensor):
        raise TypeError(
            f"--hook_module output is a {type(hook_output)}, not a tensor. Pick a submodule that "
            "returns a tensor directly (re-run with --list_modules=true)."
        )
    tensor = tensor.squeeze()  # drops the size-1 batch axis, wherever it sits
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)  # a single pooled feature vector -> treat as one token
    elif tensor.ndim > 2:
        tensor = tensor.reshape(-1, tensor.shape[-1])  # flatten any extra sequence/spatial dims
    return tensor


class LatentPointCloudProjector:
    """Projects latent tokens down to 3D with a *frozen* PCA basis.

    The basis is fit once, from the first `warmup_frames` calls to `update_and_project`, and then
    reused for every subsequent frame. Refitting a fresh PCA every frame would make the point
    cloud spin/jitter arbitrarily since the top components can rotate and flip from one frame's
    tokens to the next; freezing it after a warm-up gives stable, comparable coordinates over time.
    """

    def __init__(self, warmup_frames: int = 30, n_components: int = 3):
        self.warmup_frames = warmup_frames
        self.n_components = n_components
        self._buffer: list[Tensor] = []
        self.mean: Tensor | None = None
        self.components: Tensor | None = None  # (hidden_dim, n_components)

    @property
    def is_fitted(self) -> bool:
        return self.components is not None

    def _maybe_fit(self) -> None:
        if self.is_fitted or len(self._buffer) < self.warmup_frames:
            return
        tokens = torch.cat(self._buffer, dim=0).float()  # (N, D)
        self.mean = tokens.mean(dim=0)
        centered = tokens - self.mean
        q = min(self.n_components + 2, *centered.shape)
        _, _, v = torch.pca_lowrank(centered, q=q)
        self.components = v[:, : self.n_components]
        self._buffer.clear()
        logger.info("Fitted frozen PCA projection from %d warm-up tokens.", tokens.shape[0])

    def update_and_project(self, tokens: Tensor) -> np.ndarray | None:
        """Returns (num_tokens, 3) coordinates, or None while still warming up."""
        tokens = tokens.detach().float().cpu()
        if not self.is_fitted:
            self._buffer.append(tokens)
            self._maybe_fit()
            if not self.is_fitted:
                return None
        centered = tokens - self.mean
        return (centered @ self.components).numpy()


def token_colors(n: int) -> np.ndarray:
    """Deterministic per-token-index colors (stable across frames, since token order/count is
    stable for a given architecture) so you can visually track individual tokens over time."""
    hues = np.linspace(0.0, 1.0, num=max(n, 1), endpoint=False)
    rgb = [colorsys.hsv_to_rgb(h, 0.65, 0.95) for h in hues]
    return (np.array(rgb) * 255).astype(np.uint8)


# --------------------------------------------------------------------------------------------
# Rerun wiring
# --------------------------------------------------------------------------------------------


def send_custom_blueprint(image_keys: list[str]) -> None:
    """Sends a blueprint with one 2D view per camera plus a 3D view for the latent point cloud,
    then marks `log_rerun_data`'s internal blueprint cache as populated so its own auto-blueprint
    logic (built for camera/observation/action views only) doesn't overwrite ours on first call.
    """
    import rerun as rr
    import rerun.blueprint as rrb

    image_views = [rrb.Spatial2DView(origin=key, name=key) for key in sorted(image_keys)]
    latent_view = rrb.Spatial3DView(origin="latent", name="policy latent tokens")

    blueprint = rrb.Blueprint(rrb.Horizontal(rrb.Grid(*image_views), latent_view))
    rr.send_blueprint(blueprint)
    log_rerun_data.blueprint = blueprint  # prevents log_rerun_data from sending its own


from collections import deque

# Keep the last 20 frames
_TRAIL_LENGTH = 50
_trail = deque(maxlen=_TRAIL_LENGTH)


def log_latent_point_cloud(step: int, tokens: Tensor, projector: LatentPointCloudProjector) -> None:
    import rerun as rr

    positions = projector.update_and_project(tokens)
    if positions is None:
        return

    _trail.append(positions.copy())

    all_positions = []
    all_colors = []
    all_radii = []

    base_colors = token_colors(positions.shape[0])

    for age, pts in enumerate(_trail):
        # Newest frame has fade=1, oldest has fade≈0
        fade = (age + 1) / len(_trail)

        # If your Rerun version supports RGBA:
        rgba = np.concatenate([
            base_colors,
            np.full((len(base_colors), 1), int(255 * fade), dtype=np.uint8)
        ], axis=1)

        all_positions.append(pts)
        all_colors.append(rgba)
        all_radii.append(np.full(len(pts), 0.01 * fade))

    rr.log(
        "latent/tokens",
        rr.Points3D(
            np.concatenate(all_positions),
            colors=np.concatenate(all_colors),
            radii=np.concatenate(all_radii),
        ),
    )


def log_synced_images(observation: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Logs camera images on the *current* Rerun time cursor and returns the remaining
    (non-image) keys for the caller to log separately (e.g. via `log_rerun_data`).

    `log_rerun_data` logs images with `static=True`, which is the right call for live
    robot-control streaming (only "now" matters, no need to retain every historical frame) but
    means the image stays pinned to whatever was logged last instead of advancing with the
    timeline -- so scrubbing a recorded dataset episode desyncs the video from everything else
    (like the latent point cloud) that *is* logged per-timestamp. This mirrors how LeRobot's own
    `lerobot_dataset_viz.py` logs images for scrubbable playback.
    """
    import rerun as rr

    remaining: dict[str, np.ndarray] = {}
    for key, arr in observation.items():
        if not isinstance(arr, np.ndarray) or "image" not in key:
            remaining[key] = arr
            continue
        img = arr
        if img.ndim == 3 and img.shape[0] in (1, 3, 4) and img.shape[-1] not in (1, 3, 4):
            img = np.transpose(img, (1, 2, 0))  # CHW -> HWC
        if img.dtype != np.uint8:
            img = (np.clip(img, 0.0, 1.0) * 255).astype(np.uint8)
        rr.log(key, rr.Image(img))
    return remaining


def batch_to_numpy_observation(batch: dict) -> dict[str, np.ndarray]:
    """Strips the batch_size=1 axis and converts a dataset batch to the numpy dict shape that
    `log_rerun_data` / the Robot API expects."""
    obs = {}
    for key, value in batch.items():
        if not torch.is_tensor(value):
            continue
        if not (key.startswith("observation.") or key == "action"):
            continue
        obs[key] = value[0].cpu().numpy()
    return obs


# --------------------------------------------------------------------------------------------
# Policy / hook setup shared by both sources
# --------------------------------------------------------------------------------------------


def load_policy(cfg: LatentVizConfig, ds_meta: LeRobotDatasetMetadata | None = None):
    policy_cls = get_policy_class(cfg.policy.type)
    policy = policy_cls.from_pretrained(cfg.policy.pretrained_path, config=cfg.policy)
    policy.to(cfg.device)
    policy.eval()

    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=cfg.policy,
        pretrained_path=cfg.policy.pretrained_path,
        preprocessor_overrides={"device_processor": {"device": cfg.device}},
    )
    return policy, preprocessor, postprocessor


def attach_hook(policy, dotted_path: str) -> dict:
    """Registers a forward hook on `policy.<dotted_path>` and returns a mutable dict that the hook
    writes into. `state["tokens"]` holds the latest (num_tokens, hidden_dim) tensor, and is reset
    to None after every read so callers can tell whether the hooked module actually ran on a given
    policy call. This matters in --source=robot mode, which calls select_action(): e.g. ACT only
    calls `model.encoder` when its action queue is refilled, not on every select_action() call.
    --source=dataset mode uses predict_action_chunk() instead, which always runs the model fresh,
    so the hook fires every frame there."""
    module = resolve_module(policy, dotted_path)
    state: dict = {"tokens": None}

    def _hook(_module, _inputs, output):
        state["tokens"] = extract_tokens(output)

    module.register_forward_hook(_hook)
    return state


def maybe_list_modules(cfg: LatentVizConfig, policy) -> bool:
    if not cfg.list_modules:
        return False
    print(f"Named submodules of {policy.__class__.__name__} (pick one for --hook_module):\n")
    for name, module in policy.named_modules():
        if name:
            print(f"  {name:<50s} {module.__class__.__name__}")
    return True


# --------------------------------------------------------------------------------------------
# Dataset source
# --------------------------------------------------------------------------------------------


def run_on_dataset(cfg: LatentVizConfig) -> None:
    ds_meta = LeRobotDatasetMetadata(cfg.dataset_repo_id)
    policy, preprocessor, _postprocessor = load_policy(cfg, ds_meta)

    if maybe_list_modules(cfg, policy):
        return

    hook_state = attach_hook(policy, cfg.hook_module)
    projector = LatentPointCloudProjector(warmup_frames=cfg.warmup_frames)

    delta_timestamps = resolve_delta_timestamps(cfg.policy, ds_meta)
    dataset = LeRobotDataset(cfg.dataset_repo_id, episodes=[cfg.episode], delta_timestamps=delta_timestamps)
    loader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=False)

    init_rerun(session_name="lerobot_latent_pointcloud", ip=cfg.display_ip, port=cfg.display_port)
    image_keys = [k for k in dataset.meta.camera_keys]
    send_custom_blueprint(image_keys)

    try:
        import rerun as rr

        for step, batch in enumerate(loader):
            if step >= cfg.max_steps:
                break
            raw_obs = batch_to_numpy_observation(batch)
            action_np = raw_obs.pop("action", None)

            model_batch = preprocessor(batch)
            with torch.no_grad():
                # Unlike select_action(), predict_action_chunk() always runs a fresh forward pass
                # through the model (no action-queue caching), so the hook fires every frame here.
                # select_action() would only re-run the model (and fire the hook) once per action
                # chunk -- e.g. once every 100 frames for a typical ACT checkpoint -- which for a
                # single dataset episode may never reach --warmup_frames, leaving the point cloud
                # empty. We don't need the queue's caching here since we're not actually executing
                # actions on a robot, just visualizing.
                policy.predict_action_chunk(model_batch)

            rr.set_time("frame_index", sequence=step)
            if "timestamp" in batch:
                rr.set_time("timestamp", timestamp=batch["timestamp"][0].item())
            remaining_obs = log_synced_images(raw_obs)
            log_rerun_data(
                observation=remaining_obs, action={"dataset": action_np} if action_np is not None else None
            )
            if hook_state["tokens"] is not None:
                log_latent_point_cloud(step, hook_state["tokens"], projector)
                hook_state["tokens"] = None
    finally:
        shutdown_rerun()


# --------------------------------------------------------------------------------------------
# Real-robot source
# --------------------------------------------------------------------------------------------


def run_on_robot(cfg: LatentVizConfig) -> None:
    # The policy needs dataset-shaped feature metadata (keys/shapes) to build model-ready
    # observations from raw robot observations, exactly like the ACT tutorial example.
    if not cfg.dataset_repo_id:
        raise ValueError(
            "--dataset_repo_id is required even in --source=robot mode: it supplies the feature "
            "schema (camera/state keys and shapes) the policy was trained with. Pass the repo_id "
            "of the dataset used to train --policy.path."
        )
    ds_meta = LeRobotDatasetMetadata(cfg.dataset_repo_id)
    policy, preprocessor, postprocessor = load_policy(cfg, ds_meta)

    if maybe_list_modules(cfg, policy):
        return

    hook_state = attach_hook(policy, cfg.hook_module)
    projector = LatentPointCloudProjector(warmup_frames=cfg.warmup_frames)

    robot = make_robot_from_config(cfg.robot)
    robot.connect()

    init_rerun(session_name="lerobot_latent_pointcloud", ip=cfg.display_ip, port=cfg.display_port)
    image_keys = [k for k in ds_meta.camera_keys]
    send_custom_blueprint(image_keys)

    period = 1.0 / cfg.fps
    try:
        import rerun as rr

        for step in range(cfg.max_steps):
            start = time.perf_counter()

            obs = robot.get_observation()
            obs_frame = build_inference_frame(
                observation=obs, device=cfg.device, ds_features=ds_meta.features, task=cfg.task
            )
            model_batch = preprocessor(obs_frame)

            with torch.no_grad():
                action = policy.select_action(model_batch)
            action = postprocessor(action)
            robot_action = make_robot_action(action, ds_meta.features)
            robot.send_action(robot_action)

            rr.set_time("frame_index", sequence=step)
            log_rerun_data(observation=obs, action=robot_action)
            if hook_state["tokens"] is not None:
                log_latent_point_cloud(step, hook_state["tokens"], projector)
                hook_state["tokens"] = None

            elapsed = time.perf_counter() - start
            if elapsed < period:
                time.sleep(period - elapsed)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        robot.disconnect()
        shutdown_rerun()


# --------------------------------------------------------------------------------------------


@parser.wrap()
def main(cfg: LatentVizConfig) -> None:
    init_logging()
    logger.info("Config: %s", cfg)

    if cfg.source == "dataset":
        run_on_dataset(cfg)
    else:
        run_on_robot(cfg)


if __name__ == "__main__":
    main()
