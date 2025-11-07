#!/usr/bin/env python
"""
Example script for recording data with UR5e robot.

Before running:
1. Install ur_rtde: pip install ur-rtde
   OR install urx: pip install urx
2. Make sure your UR5e controller is accessible on the network
3. Set the robot controller to Remote Control mode
4. Update the IP address in the configuration below
"""

from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.record import record, DatasetRecordConfig, RecordConfig
from lerobot.robots.ur5e import UR5eConfig, UR5eRobot
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig

# Configuration
ROBOT_IP = "192.168.1.100"  # Update with your UR5e IP address
ROBOT_ID = "my_ur5e"
HF_USERNAME = "your_username"  # Update with your HuggingFace username
DATASET_NAME = "ur5e_pick_place"
NUM_EPISODES = 10
FPS = 30
EPISODE_TIME_S = 60

# Create robot configuration
robot_config = UR5eConfig(
    ip_address=ROBOT_IP,
    id=ROBOT_ID,
    cameras={
        "front": OpenCVCameraConfig(
            index_or_path=0,  # Camera index, adjust if needed
            width=640,
            height=480,
            fps=FPS,
        )
    },
    max_joint_velocity=1.0,  # rad/s - adjust for safety
    max_joint_acceleration=1.0,  # rad/s² - adjust for safety
    max_relative_target=0.1,  # rad - safety limit per step
    use_degrees=False,  # Use radians (recommended)
)

# Create teleoperator configuration (keyboard control)
teleop_config = KeyboardTeleopConfig()

# Create dataset configuration
dataset_config = DatasetRecordConfig(
    repo_id=f"{HF_USERNAME}/{DATASET_NAME}",
    single_task="Pick and place the object",
    num_episodes=NUM_EPISODES,
    fps=FPS,
    episode_time_s=EPISODE_TIME_S,
    push_to_hub=True,  # Set to False to only save locally
    private=False,  # Set to True for private dataset
)

# Create record configuration
record_config = RecordConfig(
    robot=robot_config,
    dataset=dataset_config,
    teleop=teleop_config,
    display_data=True,  # Show camera feed
    play_sounds=True,  # Audio feedback
)

if __name__ == "__main__":
    print("Starting UR5e data recording...")
    print(f"Robot IP: {ROBOT_IP}")
    print(f"Dataset: {HF_USERNAME}/{DATASET_NAME}")
    print(f"Episodes: {NUM_EPISODES}")
    print("\nMake sure:")
    print("1. UR5e controller is in Remote Control mode")
    print("2. Robot is in a safe starting position")
    print("3. Camera is connected and working")
    print("\nPress Ctrl+C to stop recording")
    
    # Start recording
    dataset = record(record_config)
    print(f"\nRecording complete! Dataset saved to: {dataset.root}")

