#!/usr/bin/env python

# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
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

from dataclasses import dataclass, field

from lerobot.cameras import CameraConfig
from lerobot.cameras.configs import Cv2Rotation
from lerobot.cameras.opencv import OpenCVCameraConfig
from lerobot.cameras.orbbec import OrbbecCameraConfig
from lerobot.cameras.realsense import RealSenseCameraConfig

from ..config import RobotConfig


@RobotConfig.register_subclass("ur5e")
@dataclass
class UR5eConfig(RobotConfig):
    # 机器人IP地址
    robot_ip: str = "192.168.31.2"
    
    cameras: dict[str, CameraConfig] = field(
        default_factory=lambda: {
            "webcam": OrbbecCameraConfig(
                serial_number_or_index=1,  # 相机索引或序列号
                fps=30,
                width=640,   # 相机实际支持的分辨率宽度
                height=480,  # 相机实际支持的分辨率高度
            ),
            # "wrist_camera": OpenCVCameraConfig(
            #     index_or_path=10,  # 更新为实际可用的相机索引
            #     fps=30,
            #     width=640,
            #     height=480,
            #     rotation=Cv2Rotation.ROTATE_180,  # 旋转180度（倒置）
            # ),
        }
    )

# v4l2-ctl --list-devices