#!/usr/bin/env python


import logging
from typing import Any

import numpy as np

from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from ..teleoperator import Teleoperator
from .configuration_vision_pro import VisionProTeleopConfig
from .vp_lib.vr import VRSource
from .vp_lib.vr2ur import reorder_homogeneous, VRArmMapper, transform_matrix_to_tcp_coords
from .vp_lib.ur_math import rotation_vector_to_matrix

# 导入 UR5eRobot 以访问活动实例
try:
    from lerobot.robots.ur5e.ur5e import UR5eRobot
except ImportError:
    UR5eRobot = None

logger = logging.getLogger(__name__)


class VisionProTeleop(Teleoperator):
    config_class = VisionProTeleopConfig
    name = "vision_pro"

    def __init__(self, config: VisionProTeleopConfig):
        super().__init__(config)
        self.config = config
        self.vr_source: VRSource | None = None
        self.last_action = None
        self.calibration_data = {}
        self.vr_arm_mapper = VRArmMapper()  # VR 到机械臂的映射器
        self._robot = config.robot  # 存储配置中的 robot（如果有）
        # self.robot = None
        self.robot = UR5eRobot.get_active_instance()
        self._prev_tcp: list[float] | None = None  # 记录上一次的 TCP pose，用于步进限制

    @property
    def action_features(self) -> dict:
        return {
            "joint_1.pos": float,
            "joint_2.pos": float,
            "joint_3.pos": float,
            "joint_4.pos": float,
            "joint_5.pos": float,
            "joint_6.pos": float,
            "hand_pos": float,  # 夹爪位置
        }

    @property
    def feedback_features(self) -> dict:
        return {}  # Vision Pro 可能不需要反馈，或者根据实际需求实现

    @property
    def is_connected(self) -> bool:
        """检查 Vision Pro 是否已连接"""
        return self.vr_source is not None

    @property
    def is_calibrated(self) -> bool:
        """检查是否已校准"""
        return self.vr_arm_mapper.is_calibrated

    def connect(self, calibrate: bool = True, tcp_pose: list[float] | np.ndarray | None = None, robot: Any = None) -> None:
        """
        连接到 Vision Pro 设备
        
        Args:
            calibrate: 是否在连接后自动校准
            tcp_pose: TCP pose [x, y, z, rx, ry, rz]（用于标定，可选）
            robot: 机器人实例（用于获取 TCP pose，可选，如果提供了 tcp_pose 则不需要）
        """
        if self.is_connected:
            raise DeviceAlreadyConnectedError(
                f"{self} is already connected. Do not run `connect()` twice."
            )

        try:
            self.vr_source = VRSource(
                mode=self.config.mode,
                recording_file=self.config.recording_file,
                host=self.config.host
            )
            self.last_action = None
            
            if calibrate:
                # 优先使用传入的 tcp_pose，否则从 robot 获取，最后使用 config.tcp_pose
                tcp_pose_to_use = tcp_pose or self.config.tcp_pose
                if tcp_pose_to_use is not None:
                    self.calibrate(tcp_pose=tcp_pose_to_use)
                elif robot is not None:
                    # 如果提供了 robot 实例，从 robot 获取 TCP pose
                    self.calibrate(robot=robot)
                else:
                    logger.warning(
                        "Calibration requested but no TCP pose or robot instance provided. "
                        "Skipping calibration. Call calibrate(tcp_pose=...) or calibrate(robot=...) manually."
                    )
                
            logger.info(f"{self} connected successfully (mode: {self.config.mode}).")
            
        except Exception as e:
            self.vr_source = None
            raise ConnectionError(f"Failed to connect to {self}: {e}") from e

    def calibrate(self, tcp_pose: list[float] | np.ndarray | None = None, robot: Any = None) -> None:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        
        # 获取 TCP pose：优先使用传入的 tcp_pose，否则从 robot 获取，最后使用 config.tcp_pose
        tcp_pose_to_use = None

        tcp_pose_to_use = self.robot.r_inter.getActualTCPPose()
    
        logger.info("进行标定...")
        
        # 1. 从 VR 获取当前手腕姿态
        latest = self.vr_source.latest()
        if latest is None or 'right_wrist' not in latest:
            raise RuntimeError("Failed to get VR wrist data. Please ensure VR is streaming.")
        
        right_wrist = latest.get('right_wrist')
        T_vr = right_wrist[0].copy()  # shape (4, 4)
        
        # 2. 在 z 轴方向平移 0.1
        T_translate_z = np.eye(4)
        T_translate_z[2, 3] = 0.1
        T_vr = T_vr @ T_translate_z
        
        # 3. 转换坐标系（VR 坐标系 -> 机械臂坐标系）
        T_vr = reorder_homogeneous(T_vr)
        logger.info(f"由 right_wrist 计算得到的齐次变换矩阵 T_vr:\n{T_vr}")
        
        # 4. 使用提供的 TCP pose
        logger.info(f"当前 TCP pose (旋转矢量): {[round(x, 3) for x in tcp_pose_to_use]}")
        
        # 5. 将 TCP pose（旋转矢量）转换为齐次变换矩阵
        T_tcp = rotation_vector_to_matrix(tcp_pose_to_use)
        logger.info(f"由 tcp_pose 计算得到的齐次变换矩阵 T_tcp:\n{T_tcp}")
        
        # 6. 执行标定
        T_vr_hand_init = self.vr_arm_mapper.calibrate(T_vr, T_tcp)
        logger.info(f"标定完成！T_vr_hand_init:\n{T_vr_hand_init}")
        
        # 保存校准数据到 calibration_data（用于兼容性）
        self.calibration_data = {
            "T_vr_hand_init": T_vr_hand_init.tolist(),
            "T_tcp_init": T_tcp.tolist(),
        }
        
        logger.info(f"{self} calibration completed.")

    def configure(self) -> None:
        """配置 Vision Pro 设备（当前无需额外配置）"""
        pass

    def get_action(self) -> dict[str, Any]:
        """从 Vision Pro 获取当前动作"""
        if not self.is_connected:
            raise DeviceNotConnectedError(
                f"{self} is not connected. You need to run `connect()` before `get_action()`."
            )

        if not self.is_calibrated:
            raise RuntimeError(
                f"{self} is not calibrated. Please call `calibrate()` before `get_action()`."
            )

        try:
            latest = self.vr_source.latest()
            if latest is None:
                if self.last_action is not None:
                    return self.last_action
                return self._get_zero_action()
            
            # 1. 获取 VR 手腕姿态
            right_wrist = latest.get('right_wrist')
            if right_wrist is None:
                if self.last_action is not None:
                    return self.last_action
                return self._get_zero_action()
            
            vr_wrist = right_wrist[0].copy()  # shape (4, 4)
            
            # 2. 转换坐标系（VR 坐标系 -> 机械臂坐标系）
            vr_wrist = reorder_homogeneous(vr_wrist)
            
            # 3. 使用 VRArmMapper 计算目标机械臂姿态
            T_arm_ee = self.vr_arm_mapper.update(vr_wrist)
            
            # 4. 将齐次变换矩阵转换为 TCP pose [x, y, z, rx, ry, rz]
            tcp_cmd = transform_matrix_to_tcp_coords(T_arm_ee)
            
            # 5. 应用 TCP 步进和范围限制
            tcp_cmd = self._limit_tcp_pose(tcp_cmd)
            
            joints = self.robot.latest_joints
            tcp2joint = self.robot.robot1.getInverseKinematics(tcp_cmd, joints)
            print("(tcp2joint):", tcp2joint)
            

            # hand 

            right_fingers = latest.get('right_pinch_distance')
            print(right_fingers)
            # right_fingers 值在 0~0.1
            # 做归一化到 0~1
            right_fingers = min(max((right_fingers - 0.0) / 0.1, 0.0), 1.0)

            action = {
                "joint_1.pos": float(tcp2joint[0]),
                "joint_2.pos": float(tcp2joint[1]),
                "joint_3.pos": float(tcp2joint[2]),
                "joint_4.pos": float(tcp2joint[3]),
                "joint_5.pos": float(tcp2joint[4]),
                "joint_6.pos": float(tcp2joint[5]),
                "hand_pos": float(right_fingers),
            }
            return action

        except Exception as e:
            logger.error(f"Failed to get action from {self}: {e}")
            return self._get_zero_action()
    
    def _limit_tcp_pose(self, tcp_cmd: list[float] | np.ndarray) -> list[float]:
        """
        对 TCP pose 进行步进和范围限制
        
        Args:
            tcp_cmd: 目标 TCP pose [x, y, z, rx, ry, rz]
            
        Returns:
            限制后的 TCP pose [x, y, z, rx, ry, rz]
        """
        tcp_cmd = np.asarray(tcp_cmd)
        
        # 获取上一次的 TCP pose（优先使用类内部记录的，否则从机器人获取）
        if self._prev_tcp is not None:
            prev_tcp = np.asarray(self._prev_tcp)
        elif self.robot is not None and hasattr(self.robot, 'latest_tcp_pose') and self.robot.latest_tcp_pose is not None:
            prev_tcp = np.asarray(self.robot.latest_tcp_pose)
        elif self.robot is not None and hasattr(self.robot, 'r_inter') and self.robot.r_inter is not None:
            prev_tcp = np.asarray(self.robot.r_inter.getActualTCPPose())
        else:
            # 如果没有上一帧数据，使用当前值作为初始值（第一次调用时）
            prev_tcp = tcp_cmd.copy()
        
        step = self.config.tcp_step
        
        # 对每个维度做步进限制，以及 clamp 到设定范围
        tcp_cmd_limited = []
        limits = [
            self.config.tcp_x_limits,
            self.config.tcp_y_limits,
            self.config.tcp_z_limits,
            (-np.inf, np.inf),  # rx 不限制
            (-np.inf, np.inf),  # ry 不限制
            (-np.inf, np.inf),  # rz 不限制
        ]
        
        for i, (v, prev, (low, high)) in enumerate(zip(tcp_cmd, prev_tcp, limits)):
            # 只对前3维（x, y, z）做步进和范围限制
            if i < 3:
                # 步进限制（clip 本帧变化最多 step）
                delta = v - prev
                delta = np.clip(delta, -step, step)
                val = prev + delta
                # 限定范围
                val = np.clip(val, low, high)
                tcp_cmd_limited.append(float(val))
            else:
                # 对于旋转部分（rx, ry, rz），不做步进和范围限制
                tcp_cmd_limited.append(float(v))
        
        # 记录本次的 TCP pose，作为下一次的 prev_tcp
        self._prev_tcp = tcp_cmd_limited.copy()
        
        return tcp_cmd_limited

    def send_feedback(self, feedback: dict[str, Any]) -> None:
        """向 Vision Pro 发送反馈（当前不支持）"""
        pass

    def disconnect(self) -> None:
        """断开与 Vision Pro 的连接"""
        if not self.is_connected:
            raise DeviceNotConnectedError(
                f"{self} is not connected. You need to run `connect()` before `disconnect()`."
            )
        
        self.vr_source = None
        logger.info(f"{self} disconnected.")

