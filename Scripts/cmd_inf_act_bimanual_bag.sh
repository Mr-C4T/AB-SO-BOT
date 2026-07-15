lerobot-rollout \
  --strategy.type=base \
  --robot.type=bi_so_follower \
  --robot.left_arm_config.port=/dev/ttyACM1 \
  --robot.right_arm_config.port=/dev/ttyACM0 \
  --robot.id=my_bimanual_follower \
  --robot.calibration_dir=calib/ \
  \
  --robot.cameras='{
    head: {
      type: intelrealsense,
      serial_number_or_name: 134322073085,
      width: 640,
      height: 480,
      fps: 30
    },
    left_wrist: {
      type: intelrealsense,
      serial_number_or_name: 335122272422,
      width: 640,
      height: 480,
      fps: 30
    },
    right_wrist: {
      type: intelrealsense,
      serial_number_or_name: 335122270234,
      width: 640,
      height: 480,
      fps: 30
    }
  }' \
  \
  --task="put object in bag" \
  --policy.path=/home/katnips/bat/outputs/act_bimanual_bag/checkpoints/last/pretrained_model \
  --display_data=true \
  --policy.n_action_steps=75

