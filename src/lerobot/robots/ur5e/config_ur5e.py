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
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig

from ..config import RobotConfig


@RobotConfig.register_subclass("ur5e")
@dataclass
class UR5eConfig(RobotConfig):
    # 机器人IP地址
    robot_ip: str = "192.168.31.2"
    # 相机ID
    camera_id: int = 0
    
    # 相机配置
    # 注意：如果相机索引不正确，请使用 lerobot-find-cameras opencv 命令查找正确的索引
    # 或者直接使用设备路径，例如：index_or_path="/dev/video6"
    # 如果相机不支持指定的分辨率，可以不设置 width 和 height，让相机使用默认分辨率
    cameras: dict[str, CameraConfig] = field(
        default_factory=lambda: {
            "webcam": OpenCVCameraConfig(
                index_or_path=6,  # 更新为实际可用的相机索引
                fps=30,
                width=640,   # 相机实际支持的分辨率宽度
                height=480,  # 相机实际支持的分辨率高度
                # 注意：相机实际输出是 640x480，会在 get_observation 中调整到 480x480
            ),
            # 如果只有一个相机，注释掉第二个相机
            # "wrist_camera": OpenCVCameraConfig(
            #     index_or_path=1,
            #     fps=30,
            # ),
        }
    )
