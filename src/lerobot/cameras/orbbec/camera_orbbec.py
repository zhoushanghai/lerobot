import logging
import sys
import time
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any

import cv2
import numpy as np

# Import Orbbec SDK
try:
    from pyorbbecsdk import *  # type: ignore
except ImportError:
    # Try importing from the local ur5e_lib path
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "robots" / "ur5e" / "ur5e_lib"))
        from pyorbbecsdk import *  # type: ignore
    except ImportError as e:
        logging.warning(f"Could not import pyorbbecsdk: {e}")
        raise

# Import frame_to_bgr_image from Orbbec SDK examples
# Path: src/lerobot/robots/ur5e/ur5e_lib/pyorbbecsdk/examples/utils.py
# From: src/lerobot/cameras/orbbec/camera_orbbec.py
# So: parent.parent.parent = src/lerobot/
utils_path = Path(__file__).parent.parent.parent / "robots" / "ur5e" / "ur5e_lib" / "pyorbbecsdk" / "examples" / "utils.py"
if not utils_path.exists():
    raise ImportError(f"Could not find Orbbec SDK utils.py at {utils_path}")

import importlib.util
spec = importlib.util.spec_from_file_location("orbbec_utils", utils_path)
orbbec_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(orbbec_utils)
frame_to_bgr_image = orbbec_utils.frame_to_bgr_image

from lerobot.errors import DeviceAlreadyConnectedError, DeviceNotConnectedError

from ..camera import Camera
from ..configs import ColorMode
from ..utils import get_cv2_rotation
from .configuration_orbbec import OrbbecCameraConfig

logger = logging.getLogger(__name__)

class OrbbecCamera(Camera):

    def __init__(self, config: OrbbecCameraConfig):
        super().__init__(config)
        
        self.config = config
        self.serial_number_or_index = config.serial_number_or_index
        self.fps = config.fps
        self.color_mode = config.color_mode
        self.warmup_s = config.warmup_s
        self.rotation: int | None = get_cv2_rotation(config.rotation)

        self.pipeline: Any | None = None  # Pipeline from pyorbbecsdk
        self.device: Any | None = None  # Device from pyorbbecsdk

        # 用于异步读取的后台线程
        self.thread: Thread | None = None
        self.stop_event: Event | None = None
        self.frame_lock: Lock = Lock()
        self.latest_frame: np.ndarray | None = None
        self.new_frame_event: Event = Event()

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.serial_number_or_index})"

    @property
    def is_connected(self) -> bool:
        """检查相机是否已连接"""
        return self.pipeline is not None

    def connect(self, warmup: bool = True) -> None:
        self.pipeline = Pipeline()  # type: ignore
        config = Config()  # type: ignore
        try:
            profile_list = self.pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)  # type: ignore
            
            # 尝试获取请求的 profile，失败则使用默认（参考 color.py）
            if self.width and self.height and self.fps:
                try:
                    color_profile = profile_list.get_video_stream_profile(  # type: ignore
                        self.width, 0, OBFormat.RGB, self.fps  # type: ignore
                    )
                except OBError:  # type: ignore
                    logger.warning(f"Requested profile not available, using default.")
                    color_profile = profile_list.get_default_video_stream_profile()
            else:
                color_profile = profile_list.get_default_video_stream_profile()
            
            config.enable_stream(color_profile)
            self.pipeline.start(config)
            
            # 更新实际分辨率
            if self.width is None or self.height is None:
                self.width = color_profile.get_width()
                self.height = color_profile.get_height()
            if self.fps is None:
                self.fps = color_profile.get_fps()
                
        except Exception as e:
            self.pipeline = None
            raise ConnectionError(f"Failed to start {self}: {e}") from e

        # Warmup
        if warmup:
            for _ in range(int(self.warmup_s * 10)):
                try:
                    self.read()
                except Exception:
                    pass
                time.sleep(0.1)

        logger.info(f"{self} connected.")

    def read(self, color_mode: ColorMode | None = None, timeout_ms: int = 100) -> np.ndarray:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        # 参考 color.py 的逻辑
        frames = self.pipeline.wait_for_frames(timeout_ms)  # type: ignore
        if frames is None:
            raise RuntimeError(f"{self} read failed: no frames received.")

        color_frame = frames.get_color_frame()
        if color_frame is None:
            raise RuntimeError(f"{self} read failed: no color frame.")

        # 转换为 BGR 图像（参考 color.py）
        color_image = frame_to_bgr_image(color_frame)
        if color_image is None:
            raise RuntimeError(f"{self} read failed: frame conversion failed.")

        # 转换为 RGB（如果需要）
        if self.color_mode == ColorMode.RGB:
            color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
        
        # 应用旋转（如果需要）
        if self.rotation is not None and self.rotation in [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_180]:
            color_image = cv2.rotate(color_image, self.rotation)

        return color_image

    @staticmethod
    def find_cameras() -> list[dict[str, Any]]:
        found_cameras_info = []
        
        try:
            context = Context()  # type: ignore
            device_list = context.query_devices()

            for index in range(device_list.get_count()):
                device = device_list.get_device_by_index(index)
                device_info = device.get_device_info()

                camera_info = {
                    "name": device_info.get_name(),
                    "type": "Orbbec",
                    "id": device_info.get_serial_number(),
                    "index": index,
                    "serial_number": device_info.get_serial_number(),
                    "pid": device_info.get_pid(),
                    "vid": device_info.get_vid(),
                    "firmware_version": device_info.get_firmware_version(),
                    "hardware_version": device_info.get_hardware_version(),
                    "connection_type": str(device_info.get_connection_type()),
                    "device_type": str(device_info.get_device_type()),
                }

                # 获取默认 stream profile
                try:
                    pipeline = Pipeline(device)  # type: ignore
                    profile_list = pipeline.get_stream_profile_list(OBSensorType.COLOR_SENSOR)  # type: ignore
                    default_profile = profile_list.get_default_video_stream_profile()
                    
                    camera_info["default_stream_profile"] = {
                        "format": str(default_profile.get_format()),
                        "width": default_profile.get_width(),
                        "height": default_profile.get_height(),
                        "fps": default_profile.get_fps(),
                    }
                    pipeline = None
                except Exception as e:
                    logger.warning(f"Could not get stream profile for device {index}: {e}")

                found_cameras_info.append(camera_info)

        except ImportError as e:
            logger.error(f"pyorbbecsdk not available: {e}")
        except Exception as e:
            logger.error(f"Error finding Orbbec cameras: {e}")

        return found_cameras_info

    def _read_loop(self):
        while not self.stop_event.is_set():
            try:
                color_image = self.read(timeout_ms=500)
                with self.frame_lock:
                    self.latest_frame = color_image
                self.new_frame_event.set()
            except DeviceNotConnectedError:
                break
            except Exception as e:
                logger.warning(f"Error reading frame in background thread for {self}: {e}")

    def _start_read_thread(self) -> None:
        """启动后台读取线程"""
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=0.1)
        if self.stop_event is not None:
            self.stop_event.set()

        self.stop_event = Event()
        self.thread = Thread(target=self._read_loop, args=(), name=f"{self}_read_loop")
        self.thread.daemon = True
        self.thread.start()

    def _stop_read_thread(self) -> None:
        """停止后台读取线程"""
        if self.stop_event is not None:
            self.stop_event.set()

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=2.0)

        self.thread = None
        self.stop_event = None

    def async_read(self, timeout_ms: float = 200) -> np.ndarray:
        """
        异步读取一帧
        
        使用后台线程持续读取帧，此方法返回最新帧
        """
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")

        if self.thread is None or not self.thread.is_alive():
            self._start_read_thread()

        if not self.new_frame_event.wait(timeout=timeout_ms / 1000.0):
            thread_alive = self.thread is not None and self.thread.is_alive()
            raise TimeoutError(
                f"Timed out waiting for frame from camera {self} after {timeout_ms} ms. "
                f"Read thread alive: {thread_alive}."
            )

        with self.frame_lock:
            frame = self.latest_frame
            self.new_frame_event.clear()

        if frame is None:
            raise RuntimeError(f"Internal error: Event set but no frame available for {self}.")

        return frame

    def disconnect(self) -> None:
        """
        断开相机连接
        
        参考 color.py: pipeline.stop()
        """
        if self.thread is not None:
            self._stop_read_thread()

        if self.pipeline is not None:
            try:
                self.pipeline.stop()  # 参考 color.py
            except Exception as e:
                logger.warning(f"Error stopping pipeline: {e}")
            self.pipeline = None
            self.device = None

        logger.info(f"{self} disconnected.")

