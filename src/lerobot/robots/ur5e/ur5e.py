from lerobot.cameras.utils import make_cameras_from_configs
from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from ..robot import Robot
from .config_ur5e import UR5eConfig
import numpy as np
import time
from functools import cached_property

import cv2
# Import demo_modbus from ur5e_lib directory (relative import)
from .ur5e_lib.demo_modbus import hand_control, hand_start, hand_read, write_register

from typing import Union, Optional, Any



class UR5eRobot(Robot):
    """
    LeRobot兼容的UR机械臂Robot类（6关节+1夹爪）。
    """

    config_class = UR5eConfig
    name = "ur5e"

    # 6个关节动作
    @cached_property
    def action_features(self):
        return {
            "joint_1.pos": float,
            "joint_2.pos": float,
            "joint_3.pos": float,
            "joint_4.pos": float,
            "joint_5.pos": float,
            "joint_6.pos": float,
            "hand_pos": float, 
        }

    # 观测：6关节+相机
    @property
    def _motors_ft(self) -> dict[str, type]:
        return {
            "joint_1.pos": float,
            "joint_2.pos": float,
            "joint_3.pos": float,
            "joint_4.pos": float,
            "joint_5.pos": float,
            "joint_6.pos": float,
            "hand_pos": float,
        }
    
    @property
    def _cameras_ft(self) -> dict[str, tuple]:
        # 从配置的相机中获取特征
        # 注意：这里返回的是目标分辨率（用于数据集），而不是相机实际分辨率
        # 目标分辨率统一为 480x480，以保持数据集的一致性
        # 相机实际分辨率（如 640x480）会在 get_observation 中调整到目标分辨率
        features = {}
        for cam_name, cam in self.cameras.items():
            # 目标分辨率统一为 480x480（用于数据集）
            # 如果需要使用配置中的分辨率，可以使用：
            # target_height = cam.config.height if cam.config.height else 480
            # target_width = cam.config.width if cam.config.width else 480
            # features[cam_name] = (target_height, target_width, 3)
            features[cam_name] = (480, 480, 3)
        return features
    
    @cached_property
    def observation_features(self):
        return {**self._motors_ft, **self._cameras_ft}

    def __init__(self, config: UR5eConfig):
        super().__init__(config)
        self.config = config
        self.robot_ip = config.robot_ip
        
        # 初始化变量（稍后在 connect() 中连接）
        self.robot1 = None
        self.r_inter = None
        self.ser1 = None
        self.old_hand_pose = [1000, 1000, 1000, 1000, 1000, 0]  # 初始化手部姿态
        
        # 从配置创建相机对象（使用 OpenCV 相机）
        self.cameras = make_cameras_from_configs(config.cameras)

    @property
    def is_connected(self) -> bool:
        """Whether the robot is currently connected or not."""
        # 机器人必须连接，但相机可以部分连接失败（会在 get_observation 中返回黑色图像）
        robot_connected = self.robot1 is not None and self.r_inter is not None
        return robot_connected
    
    @property
    def is_calibrated(self) -> bool:
        """Whether the robot is currently calibrated or not."""
        # UR5e 默认已校准
        return True

    def configure(self) -> None:
        """Apply any one-time or runtime configuration to the robot."""
        # 可以在这里添加机器人配置逻辑
        pass

    def connect(self, calibrate: bool = True) -> None:
        """
        Establish communication with the robot.
        
        Args:
            calibrate (bool): If True, automatically calibrate the robot after connecting if needed.
        """
        import rtde_control
        import rtde_receive
        import cv2
        
        print("Connecting to UR5e robot...")
        # 连接机器人
        self.robot1 = rtde_control.RTDEControlInterface(self.robot_ip)
        self.r_inter = rtde_receive.RTDEReceiveInterface(self.robot_ip)
        print("Robot connected successfully")
        
        # 连接相机（使用配置中的 OpenCV 相机）
        print("Connecting cameras...")
        for cam_name, cam in self.cameras.items():
            try:
                cam.connect()
                print(f"Camera '{cam_name}' connected successfully")
            except Exception as e:
                print(f"Warning: Failed to connect camera '{cam_name}': {e}")
                print("You may need to:")
                print("1. Check if the camera is connected")
                print("2. Check camera permissions (run: sudo usermod -a -G video $USER)")
                print("3. Make sure no other program is using the camera")
        
        # 初始化手部夹爪
        try:
            print("Initializing hand gripper...")
            self.ser1 = hand_start(500)
            write_register(self.ser1, 1009, 1)
            print("Hand gripper initialized")
        except Exception as e:
            print(f"Warning: Failed to initialize hand gripper: {e}")
            self.ser1 = None
        
        if calibrate and not self.is_calibrated:
            self.calibrate()
    
    def calibrate(self) -> None:
        """
        Calibrate the robot if applicable. For UR5e, this is typically a no-op.
        """
        # UR5e 不需要校准，直接返回
        pass

    def disconnect(self):
        """Disconnect from the robot and perform any necessary cleanup."""
        try:
            # 断开相机连接
            for cam in self.cameras.values():
                try:
                    cam.disconnect()
                except Exception as e:
                    print(f"Error disconnecting camera: {e}")
            
            # 断开机器人连接
            if hasattr(self, 'robot1') and self.robot1:
                self.robot1.stopScript()
                self.robot1.disconnect()
            if hasattr(self, 'r_inter') and self.r_inter:
                self.r_inter.disconnect()
        except Exception as e:
            print(f"Error during disconnect: {e}")
        finally:
            self.robot1 = None
            self.r_inter = None
    
    def get_observation(self):
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        
        # 获取关节角度
        joints = self.r_inter.getActualQ()
        print("joints:", [round(x, 3) for x in joints])
        tcp_pose = self.r_inter.getActualTCPPose()
        print("tcp_pose:", [round(x, 3) for x in tcp_pose])

        # 读取手部位置
        if self.ser1 is not None:
            try:
                hands = hand_read(self.ser1)
                if len(hands) > 0:
                    hand_pos = float(hands[0]) / 1000.0
                else:
                    hand_pos = 1.0  # 默认值（对应1000，表示张开状态）
            except Exception as e:
                print(f"Warning: Failed to read hand position: {e}")
                hand_pos = 1.0
        else:
            hand_pos = 1.0  # 默认值

        # 构建观察字典
        observation = {
            # 关节位置
            "joint_1.pos": float(joints[0]),
            "joint_2.pos": float(joints[1]),
            "joint_3.pos": float(joints[2]),
            "joint_4.pos": float(joints[3]),
            "joint_5.pos": float(joints[4]),
            "joint_6.pos": float(joints[5]),
            # 手部位置（单个值）
            "hand_pos": hand_pos,
        }
        
        # 从配置的相机中读取图像
        # 目标分辨率统一为 480x480，以匹配 observation_features
        target_height = 480
        target_width = 480
        
        for cam_key, cam in self.cameras.items():
            try:
                # 检查相机是否已连接
                if not cam.is_connected:
                    print(f"Warning: Camera '{cam_key}' is not connected, returning black image")
                    img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                    observation[cam_key] = img
                    continue
                
                # 尝试读取图像
                try:
                    img = cam.async_read(timeout_ms=500)
                    if img is None or img.size == 0:
                        # 如果读取失败，返回黑色图像
                        print(f"Warning: Camera '{cam_key}' returned empty frame")
                        img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                    else:
                        # 调整图像大小到目标分辨率（480x480）
                        # 无论相机实际分辨率是多少（如配置中的 640x480），都调整为 480x480
                        # 以匹配 observation_features 中定义的分辨率
                        if img.shape[0] != target_height or img.shape[1] != target_width:
                            img = cv2.resize(img, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
                        
                        # 确保图像格式正确：RGB, uint8, 3通道
                        if len(img.shape) == 3 and img.shape[2] == 3:
                            img = img.astype(np.uint8)
                        else:
                            print(f"Warning: Camera '{cam_key}' returned unexpected image shape: {img.shape}")
                            img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                            
                except TimeoutError as e:
                    print(f"Warning: Timeout reading from camera '{cam_key}' (timeout: 500ms): {e}")
                    img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                except Exception as e:
                    print(f"Warning: Error reading from camera '{cam_key}': {e}")
                    img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                
                observation[cam_key] = img
                
            except Exception as e:
                print(f"Warning: Failed to process camera '{cam_key}': {e}")
                print(f"  Camera info: is_connected={cam.is_connected if hasattr(cam, 'is_connected') else 'unknown'}")
                # 返回黑色图像作为占位符
                img = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                observation[cam_key] = img
        
        return observation

    def read(self):
        """Get the current state of the UR robot.

        Returns:
            tuple: (joint_positions, tcp_pose) - The current joint angles and TCP pose.
        """
        joint_pos = self.r_inter.getActualQ()
        tcp_pose = self.r_inter.getActualTCPPose()
        return joint_pos, tcp_pose

    def reset(self) -> None:
        """Reset the environment to its initial state."""
        # 重置机器人到初始位置
        tcp_pose = [-0.35,-0.4,0.330,0.126,2.286,-2.2]
        self.robot1.moveL(tcp_pose, 0.1, 0.5, False)
        # joint_pos = [-2.122, -1.749, -1.78, -2.795, -2.04, -3.126]
        # self.robot1.moveJ(joint_pos, 0.1, 0.5, False)
        time.sleep(2)
        # 重置手部位置
        hand_targets = [1000, 1000, 1000, 1000, 1000, 1000]
        hand_control(self.ser1, hand_targets)
        time.sleep(0.5)
        hand_targets = [400, 400, 400, 400, 400, 400]
        hand_control(self.ser1, hand_targets)
        time.sleep(0.5)
        hand_targets = [1000, 1000, 1000, 1000, 1000, 1000]
        hand_control(self.ser1, hand_targets)
        time.sleep(1)

        # 重置内部状态
        self.old_hand_pose = [1000, 1000, 1000, 1000, 1000, 0]
        

    def send_action(self, action: dict):
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        
        # 获取当前关节位置作为默认值（如果action中缺少某些键）
        current_joints = self.r_inter.getActualQ() if self.r_inter else [0.0] * 6
        
        # 构建完整的 action 字典，确保包含所有必需的键
        # 如果 action 中缺少某些键，使用当前关节位置
        complete_action = {}
        for i in range(6):
            key = f"joint_{i+1}.pos"
            complete_action[key] = action.get(key, current_joints[i])
        
        # 获取手部位置，如果没有则使用默认值 1.0（张开状态）
        complete_action["hand_pos"] = action.get("hand_pos", 1.0)
        
        # get joint positions from complete_action
        joint_targets = [complete_action[f"joint_{i+1}.pos"] for i in range(6)]
        
        # 使用 servoj 进行平滑运动（推荐）
        # 参数说明：servoJ(joint_positions, velocity, acceleration, lookahead_time, gain)
        # lookahead_time 必须在 [0.03, 0.2] 范围内
        try:
            velocity = 0.2
            acceleration = 0.5
            lookahead_time = 0.03  # 最小值为 0.03
            gain = 0.1
            self.robot1.servoJ(joint_targets, velocity, acceleration, lookahead_time, gain)
        except Exception as e:
            print(f"Warning: Failed to send joint command: {e}")
        
        # control hand positions
        if self.ser1 is not None:
            try:
                hand_pos_normalized = complete_action["hand_pos"]
                hand_value = int(hand_pos_normalized * 1000.0)
                hand_value = max(0, min(1000, hand_value))
                hand_targets = [hand_value, hand_value, hand_value, hand_value, hand_value, 0]
                hand_control(self.ser1, hand_targets)
            except Exception as e:
                print(f"Warning: Failed to control hand: {e}")
        
        # return actual executed action (包含所有必需的键)
        return complete_action
