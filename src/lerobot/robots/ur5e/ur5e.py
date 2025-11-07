from lerobot.cameras.utils import make_cameras_from_configs
from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from ..robot import Robot
from .config_ur5e import UR5eConfig
import numpy as np
import time
from functools import cached_property

import pyrealsense2 as rs
import cv2
#from demo_can import hand_control,hand_start,hand_read,write6
# Import demo_modbus from packages directory
from ur5e_lib.demo_modbus import hand_control, hand_start, hand_read, write_register

# 导入pyorbbecsdk相关类型
from pyorbbecsdk import *
from typing import Union, Optional, Any



class URRobotLeRobot(Robot):
    """
    LeRobot兼容的UR机械臂Robot类（6关节+1相机，无gripper）。
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
    @cached_property
    def observation_features(self):
        return {
            "joint_1.pos": float,
            "joint_2.pos": float,
            "joint_3.pos": float,
            "joint_4.pos": float,
            "joint_5.pos": float,
            "joint_6.pos": float,
            "hand_pos": float, 
            "webcam_rgb": (480, 480, 3),  # 外部相机分辨率为480x480
            "wrist_rgb":(480,480,3),
        }

    def __init__(self, config: UR5eConfig):
        super().__init__(config)
        self.config = config
        robot_ip = config.robot_ip
        camera_id = config.camera_id
        import rtde_control
        import rtde_receive
        import cv2
        print("import rtde_control")
        self.robot1 = rtde_control.RTDEControlInterface(robot_ip)
        self.r_inter = rtde_receive.RTDEReceiveInterface(robot_ip)
        #self.camera = cv2.VideoCapture(camera_id)
        self.config1 = Config()
        self.pipeline1 = Pipeline()
        #self.temporal_filter = TemporalFilter(alpha=0.85)
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        #self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        #self.config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        self.pipeline.start(self.config)
        try:
            # 获取摄像头的流配置
            profile_list = self.pipeline1.get_stream_profile_list(OBSensorType.COLOR_SENSOR)
            color_profile = None
            for cp in profile_list:
                if cp.get_format() == OBFormat.RGB and cp.get_width() == 640 and cp.get_height() == 480:
                    color_profile = cp
                    print("使用640x480的color profile")
                    break
            if color_profile is None:
                color_profile = profile_list.get_default_video_stream_profile()
                print("未找到640x480的color profile，使用默认: ", color_profile)
            self.config1.enable_stream(color_profile)

            # profile_list = self.pipeline1.get_stream_profile_list(OBSensorType.DEPTH_SENSOR)
            # depth_profile = None
            # for dp in profile_list:
            #     if dp.get_width() == 640 and dp.get_height() == 480:
            #         depth_profile = dp
            #         print("使用640x480的depth profile")
            #         break
            # if depth_profile is None:
            #     depth_profile = profile_list.get_default_video_stream_profile()
            #     print("未找到640x480的depth profile，使用默认: ", depth_profile)
            # self.config1.enable_stream(depth_profile)
        except Exception as e:
            print("配置头部摄像头失败:", e)
            return

        # 启动摄像头
        self.pipeline1.start(self.config1)
        print("import hand_start")
        #'''
        self.ser1 = hand_start(500)
        write_register(self.ser1, 1009, 1)

      
        self.old_hand_pose = [1000,1000,1000,1000,1000,0] # 初始化手部姿态（保留用于reset方法）

    @property
    def is_connected(self) -> bool:
        """Whether the robot is currently connected or not."""
        # 连接在 __init__ 中建立，这里检查连接状态
        return hasattr(self, 'robot1') and self.robot1 is not None
    
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
        # 连接已经在 __init__ 中完成，这里可以添加额外的连接逻辑
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
            if hasattr(self, 'pipeline') and self.pipeline:
                self.pipeline.stop()
            if hasattr(self, 'pipeline1') and self.pipeline1:
                self.pipeline1.stop()
            if hasattr(self, 'robot1') and self.robot1:
                self.robot1.stopScript()
                self.robot1.disconnect()
            if hasattr(self, 'r_inter') and self.r_inter:
                self.r_inter.disconnect()
        except Exception as e:
            print(f"断开连接时出错: {e}")
    
    def frame_to_bgr_image(self,frame: VideoFrame) -> Union[Optional[np.array], Any]:
        width = frame.get_width()
        height = frame.get_height()
        color_format = frame.get_format()
        data = np.asanyarray(frame.get_data())
        image = np.zeros((height, width, 3), dtype=np.uint8)
        if color_format == OBFormat.RGB:
            image = np.resize(data, (height, width, 3))
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        elif color_format == OBFormat.BGR:
            image = np.resize(data, (height, width, 3))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif color_format == OBFormat.YUYV:
            image = np.resize(data, (height, width, 2))
            image = cv2.cvtColor(image, cv2.COLOR_YUV2BGR_YUYV)
        elif color_format == OBFormat.MJPG:
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        elif color_format == OBFormat.I420:
            image = i420_to_bgr(data, width, height)
            return image
        elif color_format == OBFormat.NV12:
            image = nv12_to_bgr(data, width, height)
            return image
        elif color_format == OBFormat.NV21:
            image = nv21_to_bgr(data, width, height)
            return image
        elif color_format == OBFormat.UYVY:
            image = np.resize(data, (height, width, 2))
            image = cv2.cvtColor(image, cv2.COLOR_YUV2BGR_UYVY)
        else:
            print("Unsupported color format: {}".format(color_format))
            return None
        return image
    
    def get_observation(self):
        # 获取关节角度
        joints =self.r_inter.getActualQ()
        print("joints:", [round(x, 3) for x in joints])
        tcp_pose = self.r_inter.getActualTCPPose()
        print("tcp_pose:", [round(x, 3) for x in tcp_pose])

        hands = hand_read(self.ser1)
        # 直接读取手部的值，除以1000得到归一化的手部位置
        if len(hands) > 0:
            hand_pos = float(hands[0]) / 1000.0
        else:
            hand_pos = 1.0  # 默认值（对应1000，表示张开状态）

        # 获取手腕相机图像
        frames1 = self.pipeline.wait_for_frames()
        color_frame = frames1.get_color_frame()

        if color_frame:
            wrist_img = np.asanyarray(color_frame.get_data())
            # 截取中间正方形区域
            h, w, _ = wrist_img.shape
            side = min(h, w)
            y1 = (h - side) // 2
            x1 = (w - side) // 2
            wrist_img = wrist_img[y1:y1 + side, x1:x1 + side, :]
            # 确保是RGB格式，uint8类型，HWC形状
            wrist_img = cv2.cvtColor(wrist_img, cv2.COLOR_BGR2RGB)
            wrist_img = wrist_img.astype(np.uint8)
            # 调整图片大小为480x480（匹配 observation_features）
            wrist_img = cv2.resize(wrist_img, (480, 480))
        else:
            wrist_img = np.zeros((480, 480, 3), dtype=np.uint8)

        # 获取外部相机图像
        frames2 = self.pipeline1.wait_for_frames(10)
        if frames2:
            color_frame = frames2.get_color_frame()
            img = self.frame_to_bgr_image(color_frame)
            if img is not None and img.shape[0] > 0 and img.shape[1] > 0:
                # 截取中间正方形区域
                h, w, _ = img.shape
                side = min(h, w)
                y1 = (h - side) // 2
                x1 = (w - side) // 2
                img = img[y1:y1 + side, x1:x1 + side, :]
                # 确保是RGB格式，uint8类型，HWC形状
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = img.astype(np.uint8)
                # 调整图片大小为480x480
                img = cv2.resize(img, (480, 480))
            else:
                img = np.zeros((480, 480, 3), dtype=np.uint8)
        else:
            img = np.zeros((480, 480, 3), dtype=np.uint8)

        # 注意：必须完全匹配 observation_features 中定义的键
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
            # 图像数据（必须与 observation_features 中的键名匹配）
            "webcam_rgb": img,  # 外部相机图像
            "wrist_rgb": wrist_img,  # 手腕相机图像
        }
        
        # 保存图像到文件（可选，用于调试）
        cv2.imwrite("external_image.png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        cv2.imwrite("wrist_image.png", cv2.cvtColor(wrist_img, cv2.COLOR_RGB2BGR))

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
        # get joint positions from action
        joint_targets = [action.get(f"joint_{i+1}.pos", 0.0) for i in range(6)]
        
        # get hand positions from action
        hand_pos_normalized = action.get("hand_pos", 1.0)  # default 1.0 (对应1000，张开状态）
        hand_value = int(hand_pos_normalized * 1000.0)
        hand_value = max(0, min(1000, hand_value))
        hand_targets = [hand_value, hand_value, hand_value, hand_value, hand_value, 0]
        
        # move joint positions
        velocity = 0.2
        acceleration = 0.5
        # self.robot1.moveJ(joint_targets, velocity, acceleration, False)
        
        # control hand positions
        hand_control(self.ser1, hand_targets)
        
        # return actual executed action
        return action

    @property
    def cameras(self):
        # LeRobot用于判断有无相机
        # 返回相机字典，键名应该与 observation_features 中的相机键名匹配
        # 注意：这里返回的是实际的相机对象，LeRobot 会使用它们来读取图像
        # 但由于我们已经在 get_observation() 中手动读取了图像，这里可以返回空字典
        # 或者返回相机对象以便 LeRobot 可以自动读取
        return {}  # 空字典，因为我们已经在 get_observation() 中手动处理相机