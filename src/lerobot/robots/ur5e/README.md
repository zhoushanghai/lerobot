# UR5e Robot Integration for LeRobot

This directory contains the implementation for Universal Robots UR5e integration with LeRobot.

## Installation

You need to install one of the following libraries to communicate with UR5e:

### Option 1: ur_rtde (Recommended)
```bash
pip install ur-rtde
```

### Option 2: urx (Alternative)
```bash
pip install urx
```

## Configuration

The UR5e robot uses RTDE (Real-Time Data Exchange) protocol or urx library to communicate with the robot controller.

### Basic Configuration

```python
from lerobot.robots.ur5e import UR5eConfig, UR5eRobot
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

# Create configuration
config = UR5eConfig(
    ip_address="192.168.1.100",  # Your UR5e controller IP
    id="my_ur5e",
    cameras={
        "front": OpenCVCameraConfig(
            index_or_path=0,
            width=640,
            height=480,
            fps=30
        )
    },
    max_joint_velocity=1.0,  # rad/s
    max_joint_acceleration=1.0,  # rad/s²
    max_relative_target=0.1,  # rad (safety limit)
)

# Create robot instance
robot = UR5eRobot(config)
```

## Usage

### Recording a Dataset

```bash
lerobot-record \
    --robot.type=ur5e \
    --robot.ip_address=192.168.1.100 \
    --robot.id=my_ur5e \
    --robot.cameras='{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}' \
    --teleop.type=keyboard \
    --dataset.repo_id=your_username/ur5e_dataset \
    --dataset.num_episodes=10 \
    --dataset.single_task="Pick and place the object" \
    --dataset.fps=30 \
    --dataset.episode_time_s=60
```

## Joint Names

The UR5e has 6 degrees of freedom:
- `base_joint` - Base rotation
- `shoulder_joint` - Shoulder lift
- `elbow_joint` - Elbow flexion
- `wrist_1_joint` - Wrist 1 rotation
- `wrist_2_joint` - Wrist 2 rotation
- `wrist_3_joint` - Wrist 3 rotation

## Safety Features

- **max_joint_velocity**: Maximum joint velocity in rad/s
- **max_joint_acceleration**: Maximum joint acceleration in rad/s²
- **max_relative_target**: Maximum change in joint position per step (in radians)

## Notes

1. Make sure your UR5e controller is on the same network and accessible
2. The robot controller should be in Remote Control mode
3. For safety, always test with small movements first
4. The implementation supports both radians (default) and degrees (set `use_degrees=True`)

## Troubleshooting

### Connection Issues
- Check that the robot IP address is correct
- Ensure the robot controller is in Remote Control mode
- Verify network connectivity: `ping <robot_ip>`

### Import Errors
- Install ur_rtde: `pip install ur-rtde`
- Or install urx: `pip install urx`

### Motion Issues
- Reduce `max_joint_velocity` and `max_joint_acceleration` for smoother motion
- Adjust `max_relative_target` to limit step size

