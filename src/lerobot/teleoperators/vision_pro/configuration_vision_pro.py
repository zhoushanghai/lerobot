
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("vision_pro")
@dataclass
class VisionProTeleopConfig(TeleoperatorConfig):
    # VR 数据源参数
    mode: str = "playback"  # 'visionpro' | 'playback'
    recording_file: str | None = "visionpro_30s_recording.pkl"
    host: str = "10.7.144.112"  # Vision Pro 主机地址（visionpro 模式）
    
    # 追踪选项
    use_hand_tracking: bool = True
    use_head_tracking: bool = False
    
    # 坐标转换参数
    scale_factor: float = 1.0  # Vision Pro 坐标到机器人坐标的缩放因子
    smoothing_factor: float = 0.5  # 动作平滑因子 (0.0 = 无平滑, 1.0 = 完全平滑)
    
    # 校准参数
    calibration_file: Path | None = None
    tcp_pose: list[float] | None = field(default_factory=lambda: [-0.35, -0.4, 0.330, 0.126, 2.286, -2.2])  # TCP pose [x, y, z, rx, ry, rz]（用于标定，可选）
    robot: Any = None  # 机器人实例（可选，如果不提供会自动获取活动的 UR5eRobot 实例）

    # 每次动作更新的步进值（单位：米/弧度），决定了单次VR操作或者离散动作时 TCP 增量的大小
    # tcp_step: float = 0.05 / 30  # 单步位置步进大小 (米) 30fps
    # rot_step: float = 0.05 / 30 # 单步旋转步进大小 (弧度)
    tcp_step: float = 1  # 单步位置步进大小 (米) 30fps
    rot_step: float = 1 # 单步旋转步进大小 (弧度)
    # TCP 的运动范围
    tcp_x_limits: tuple[float, float] = (-0.4, 0.38)    # x 轴范围 (米)
    tcp_y_limits: tuple[float, float] = (-0.55,  -0.3)     # y 轴范围 (米)
    tcp_z_limits: tuple[float, float] = ( 0.20,  0.50)   # z 轴范围 (米)

