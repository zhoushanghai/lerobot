#!/usr/bin/env python3
"""
VR数据源模块：提供统一的数据获取接口
- 通过实例化选择两种模式：'visionpro' 实时流 或 'playback' 回放文件
- 只负责提供最新一帧数据，不包含控制、转换或记录逻辑
"""

from typing import Optional, Dict, Any
import pickle

from .VisionProTeleop.avp_stream import VisionProStreamer


class VRSource:
    """最小VR数据源接口"""

    def __init__(self, mode: str = "visionpro", recording_file: Optional[str] = None, host: str = "10.7.175.122"):
        """
        初始化数据源
        Args:
            mode: 'visionpro' | 'playback'
            recording_file: 当mode='playback'时，指定回放文件路径
            host: VisionPro 主机地址（实时模式）
        """
        if mode not in ("visionpro", "playback"):
            raise ValueError(f"Unsupported mode: {mode}")
        self.mode = mode
        self._streamer: Optional[VisionProStreamer] = None
        self._recording: Optional[list[Dict[str, Any]]] = None
        self._idx: int = 0

        self.have_data = True

        if self.mode == "visionpro":
            try:
                self._streamer = VisionProStreamer(host, False)
            except ConnectionError as e:
                raise ConnectionError(
                    f"Failed to connect to Vision Pro device at {host}:12345.\n"
                    f"Error: {e}\n\n"
                    "To use playback mode instead, set mode='playback' and provide a recording_file.\n"
                    "Example: --teleop.mode=playback --teleop.recording_file=visionpro_30s_recording.pkl"
                ) from e
        else:
            if not recording_file:
                raise ValueError("recording_file is required for playback mode")
            with open(recording_file, "rb") as f:
                self._recording = pickle.load(f)
            self._idx = 0

    def latest(self) -> Optional[Dict[str, Any]]:
        """
        获取最新一帧数据。
        Returns: 包含 'right_wrist'、'right_fingers' 等键的字典，或None
        """
        if self.mode == "visionpro":
            if self._streamer is None:
                return None
            return self._streamer.latest
        # playback
        if self._recording is None or self._idx >= len(self._recording):
            self.have_data = False
            return None
        frame = self._recording[self._idx]
        self._idx += 1
   
        return frame

    def reset(self) -> None:
        """重置回放进度（仅playback模式）。"""
        if self.mode == "playback" and self._recording is not None:
            self._idx = 0
            self.have_data = True
            
