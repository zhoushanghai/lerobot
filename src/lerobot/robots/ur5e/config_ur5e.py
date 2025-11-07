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
from lerobot.common.cameras import CameraConfig
from lerobot.common.cameras.opencv import OpenCVCameraConfig
from lerobot.common.robots import RobotConfig


@RobotConfig.register_subclass("ur5e")
@dataclass
class UR5eConfig(RobotConfig):
    # 机器人IP地址
    robot_ip: str = "192.168.31.2"
    # 相机ID
    camera_id: int = 0
    
    # 相机配置
    cameras: dict[str, CameraConfig] = field(
        default_factory=lambda: {
            "webcam": OpenCVCameraConfig(
                index_or_path=0,
                fps=30,
                width=480,
                height=480,
            ),
            "wrist_camera": OpenCVCameraConfig(
                index_or_path=1,
                fps=30,
                width=480,
                height=480,
            ),
        }
    )
