lerobot-record \
  --robot.type=bi_so_follower \
  --robot.left_arm_config.port=/dev/ttyACM1 \
  --robot.right_arm_config.port=/dev/ttyACM0 \
  --robot.id=my_bimanual_follower \
  --robot.calibration_dir=calib/ \
  \
  --teleop.type=bi_so_leader \
  --teleop.left_arm_config.port=/dev/ttyACM3 \
  --teleop.right_arm_config.port=/dev/ttyACM2 \
  --teleop.id=my_bimanual_leader \
  --teleop.calibration_dir=calib/ \
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
  --display_data=false \
  --dataset.repo_id=local/bimanual_bag1 \
  --dataset.single_task="put object in bag" \
  --dataset.episode_time_s=60 \
  --dataset.reset_time_s=20 \
  --dataset.num_episodes=10 \
  --resume=true
