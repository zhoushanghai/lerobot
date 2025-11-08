
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("vision_pro")
@dataclass
class VisionProTeleopConfig(TeleoperatorConfig):
    # VR 数据源参数
    mode: str = "visionpro"  # 'visionpro' | 'playback'
    recording_file: str | None = None  # 回放文件路径（playback 模式）
    host: str = "10.7.175.122"  # Vision Pro 主机地址（visionpro 模式）
    
    # 追踪选项
    use_hand_tracking: bool = True
    use_head_tracking: bool = False
    
    # 坐标转换参数
    scale_factor: float = 1.0  # Vision Pro 坐标到机器人坐标的缩放因子
    smoothing_factor: float = 0.5  # 动作平滑因子 (0.0 = 无平滑, 1.0 = 完全平滑)
    
    # 校准参数
    calibration_file: Path | None = "visionpro_30s_recording.pkl"
    tcp_pose: list[float] | None = [-0.35,-0.4,0.330,0.126,2.286,-2.2]  # TCP pose [x, y, z, rx, ry, rz]（用于标定，可选）

