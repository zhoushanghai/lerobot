#!/usr/bin/env python


import logging
from typing import Any

import numpy as np

from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from ..teleoperator import Teleoperator
from .configuration_vision_pro import VisionProTeleopConfig
from .vp_lib.vr import VRSource
from .vp_lib.vr2ur import reorder_homogeneous, VRArmMapper
from .vp_lib.ur_math import rotation_vector_to_matrix

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
        
        if tcp_pose is not None:
            tcp_pose_to_use = np.asarray(tcp_pose)
        elif robot is not None:
            # 从机器人实例获取 TCP pose
            if not hasattr(robot, 'is_connected') or not robot.is_connected:
                raise DeviceNotConnectedError("Robot is not connected. Please connect the robot first.")
            if not hasattr(robot, 'r_inter') or robot.r_inter is None:
                raise ValueError("Robot does not have r_inter interface. Please ensure robot is properly connected.")
            tcp_pose_to_use = np.asarray(robot.r_inter.getActualTCPPose())
        elif self.config.tcp_pose is not None:
            tcp_pose_to_use = np.asarray(self.config.tcp_pose)
        else:
            raise ValueError(
                "TCP pose is required for calibration. "
                "Please provide TCP pose via config.tcp_pose, calibrate(tcp_pose=...), or calibrate(robot=...) parameter."
            )
        
        # 验证 TCP pose 格式
        if tcp_pose_to_use.shape != (6,):
            raise ValueError(f"TCP pose must be a 6-element array [x, y, z, rx, ry, rz], got shape {tcp_pose_to_use.shape}")
        
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
       latest = vr_source.latest()

        right_wrist = latest.get('right_wrist')
        vr_wrist = right_wrist[0]
        print("vr_wrist_0:\n", vr_wrist)
        vr_wrist = vr2ur.reorder_homogeneous(vr_wrist)
        print("vr_wrist_180:\n", vr_wrist)
        T_arm_ee = vr2arm_mapper.update(vr_wrist)
        # print("T_arm_ee:\n", T_arm_ee)

        # T_arm_ee to tcp_pose
        tcp_cmd = vr2ur.transform_matrix_to_tcp_coords(T_arm_ee)
        print("tcp_pose:\n", tcp_cmd)
        # tcp_cmd[3] = 0.14331244103918367
        # tcp_cmd[4] = 2.310831159096738
        # tcp_cmd[5] = -1.952713280301774

        robot.robot1.servoL(tcp_cmd, speed, acceleration, time_ur, lookahead_time, gain)
        count += 1
        if count > 100:
            print("count:", count)
        
        # joints, tcp_pose = robot.read()
        # tcp2joint = robot.robot1.getInverseKinematics(tcp_cmd, joints)
        # print("(tcp2joint):", tcp2joint)

        # robot.robot1.servoJ(tcp2joint, speed, acceleration, time_ur, lookahead_time, gain)

        

        right_fingers = latest.get('right_pinch_distance')
        print(right_fingers)

        # 使用 Fingur 类处理手指数据
        # hand_targets = finger_processor.calculate_hand_actions(right_fingers,deg=True)

        # 0-4号手指都使用450-1000映射
        # right_fingers 值在 0~0.1，映射到 450-1000
        hand_targets = [1000, 1000, 1000, 1000, 1000, 400]
        pinch = right_fingers  # 0~0.1
        # 做归一化到 0~1
        pinch_norm = min(max((pinch - 0.0) / 0.1, 0.0), 1.0)

        # 0-4指：450-1000
        action_05 = int(450 + pinch_norm * (1000 - 450))
        action_05 = min(max(action_05, 450), 1000)
        for i in range(5):
            hand_targets[i] = action_05

        # print(hand_targets)
        result = hand_control(robot.ser1, hand_targets)




    def _convert_vision_pro_to_robot_action(self, latest: dict) -> dict[str, float]:
        if not self.config.use_hand_tracking or 'right_wrist' not in latest:
            return self._get_zero_action()
        
        # 提取右手腕变换矩阵 (1,4,4) -> (4,4)
        wrist_matrix = latest['right_wrist'][0]
        
        # 提取位置（变换矩阵的平移部分）
        pos = wrist_matrix[:3, 3] * self.config.scale_factor
        
        # 应用校准偏移
        if "initial_wrist" in self.calibration_data:
            initial_pos = np.array(self.calibration_data["initial_wrist"])
            pos = pos - initial_pos
        
        # 提取旋转（从变换矩阵提取欧拉角或四元数）
        # 简化：使用变换矩阵的前3列作为方向向量
        rotation_matrix = wrist_matrix[:3, :3]
        
        # 将位置和旋转映射到关节角度（这里需要根据实际机器人调整）
        # 简化示例：直接映射位置和旋转到关节
        action = {
            "joint_1.pos": float(pos[0] * 0.1),  # 需要根据实际调整
            "joint_2.pos": float(pos[1] * 0.1),
            "joint_3.pos": float(pos[2] * 0.1),
            "joint_4.pos": float(rotation_matrix[0, 0] * 0.1),
            "joint_5.pos": float(rotation_matrix[1, 1] * 0.1),
            "joint_6.pos": float(rotation_matrix[2, 2] * 0.1),
        }
        
        # 夹爪位置：使用 pinch_distance 或手指数据
        if 'right_pinch_distance' in latest:
            # pinch_distance 越大，夹爪越开（归一化到 0-1）
            pinch = latest['right_pinch_distance']
            action["hand_pos"] = float(np.clip(pinch / 0.1, 0.0, 1.0))  # 需要根据实际调整
        else:
            action["hand_pos"] = 0.5
        
        return action

    def _apply_smoothing(self, action: dict) -> dict:
        """应用动作平滑"""
        if self.last_action is None:
            self.last_action = action
            return action
        
        # 指数移动平均平滑
        smoothed = {}
        for key in action:
            smoothed[key] = (
                self.config.smoothing_factor * self.last_action.get(key, 0.0) +
                (1 - self.config.smoothing_factor) * action[key]
            )
        
        self.last_action = smoothed
        return smoothed

    def _apply_limits(self, action: dict) -> dict:
        """应用动作限制（确保在安全范围内）"""
        # TODO: 根据机器人类型设置限制
        # 示例：限制关节角度范围
        limited = action.copy()
        
        # 限制关节角度在合理范围内（根据你的机器人调整）
        for i in range(1, 7):
            key = f"joint_{i}.pos"
            if key in limited:
                limited[key] = np.clip(limited[key], -3.14, 3.14)  # ±π 弧度
        
        # 限制夹爪位置
        if "hand_pos" in limited:
            limited["hand_pos"] = np.clip(limited["hand_pos"], 0.0, 1.0)
        
        return limited

    def _get_zero_action(self) -> dict:
        """返回零动作（所有关节位置为 0）"""
        return {
            "joint_1.pos": 0.0,
            "joint_2.pos": 0.0,
            "joint_3.pos": 0.0,
            "joint_4.pos": 0.0,
            "joint_5.pos": 0.0,
            "joint_6.pos": 0.0,
            "hand_pos": 0.5,  # 夹爪半开
        }

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

