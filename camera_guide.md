# LeRobot 摄像头适配完整指南

## 📚 目录
1. [核心概念](#核心概念)
2. [适配流程概览](#适配流程概览)
3. [详细步骤](#详细步骤)
4. [示例代码](#示例代码)
5. [常见问题](#常见问题)

---

## 核心概念

### 1. 摄像头系统架构

LeRobot 的摄像头系统采用**分层架构**：

```
RobotConfig (机器人配置)
    └── cameras: dict[str, CameraConfig]  # 定义摄像头配置
         └── make_cameras_from_configs()  # 工厂函数创建摄像头实例
              └── Camera (抽象基类)
                   ├── OpenCVCamera      # OpenCV 摄像头实现
                   ├── RealSenseCamera   # RealSense 摄像头实现
                   └── Reachy2Camera     # Reachy2 摄像头实现
```

### 2. 关键组件

#### 2.1 CameraConfig (摄像头配置类)
- **作用**：定义摄像头的参数（分辨率、FPS、颜色模式等）
- **位置**：`src/lerobot/cameras/configs.py`
- **要求**：必须继承 `CameraConfig` 并使用 `@CameraConfig.register_subclass` 装饰器

#### 2.2 Camera (摄像头基类)
- **作用**：定义摄像头标准接口
- **位置**：`src/lerobot/cameras/camera.py`
- **必须实现的方法**：
  - `is_connected`：检查摄像头是否连接
  - `find_cameras()`：查找可用摄像头（静态方法）
  - `connect()`：连接摄像头
  - `read()`：同步读取一帧
  - `async_read()`：异步读取一帧
  - `disconnect()`：断开连接

#### 2.3 RobotConfig (机器人配置类)
- **作用**：定义机器人的配置，包括摄像头配置
- **位置**：`src/lerobot/robots/config.py`
- **要求**：摄像头配置中的 `width`、`height`、`fps` 必须指定（不能为 None）

---

## 适配流程概览

```
1. 了解你的摄像头
   ├── 摄像头类型（USB/网络/特殊驱动）
   ├── 支持的分辨率和 FPS
   └── 如何识别（索引/路径/序列号）

2. 选择合适的实现方式
   ├── 方式A：使用现有的摄像头实现（推荐）
   │   └── OpenCVCamera（USB摄像头）
   │   └── RealSenseCamera（RealSense摄像头）
   └── 方式B：自定义摄像头实现
       └── 继承 Camera 基类

3. 配置摄像头
   ├── 在 RobotConfig 中定义摄像头配置
   └── 指定摄像头参数（索引、分辨率、FPS等）

4. 在机器人中使用摄像头
   ├── 在 __init__ 中创建摄像头实例
   ├── 在 connect() 中连接摄像头
   ├── 在 get_observation() 中读取图像
   └── 在 disconnect() 中断开连接

5. 定义观察特征
   ├── 在 observation_features 中定义摄像头特征
   └── 确保分辨率与配置匹配
```

---

## 详细步骤

### 步骤 1：了解你的摄像头

#### 1.1 查找可用摄像头

**对于 USB 摄像头（OpenCV）：**
```bash
# 使用 LeRobot 工具
lerobot-find-cameras opencv

# 或手动检查
ls -l /dev/video*
python3 -c "import cv2; [print(f'Camera {i}: {cv2.VideoCapture(i).isOpened()}') for i in range(10)]"
```

**对于 RealSense 摄像头：**
```bash
lerobot-find-cameras realsense
```

#### 1.2 测试摄像头

```python
import cv2
import numpy as np

# 测试摄像头是否可用
cap = cv2.VideoCapture(6)  # 替换为你的摄像头索引

if cap.isOpened():
    ret, frame = cap.read()
    if ret:
        print(f"摄像头可用！分辨率: {frame.shape}")
        print(f"支持的 FPS: {cap.get(cv2.CAP_PROP_FPS)}")
        print(f"宽度: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
        print(f"高度: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    cap.release()
else:
    print("摄像头不可用")
```

### 步骤 2：选择合适的实现方式

#### 方式A：使用现有的 OpenCVCamera（推荐）

**适用场景**：
- USB 摄像头
- 网络摄像头
- 任何 OpenCV 支持的摄像头

**优点**：
- 无需编写额外代码
- 自动处理异步读取
- 已经过测试和优化

#### 方式B：自定义摄像头实现

**适用场景**：
- 需要特殊驱动的摄像头
- 需要额外功能（如深度图）
- 现有的实现不满足需求

**步骤**：
1. 创建摄像头配置类
2. 创建摄像头实现类（继承 `Camera`）
3. 在 `utils.py` 中注册新类型

---

## 示例代码

### 示例 1：使用 OpenCVCamera（最简单）

#### 1.1 在 RobotConfig 中配置摄像头

```python
# src/lerobot/robots/ur5e/config_ur5e.py
from dataclasses import dataclass, field
from lerobot.cameras import CameraConfig
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from ..config import RobotConfig

@RobotConfig.register_subclass("ur5e")
@dataclass
class UR5eConfig(RobotConfig):
    robot_ip: str = "192.168.31.2"
    
    # 摄像头配置
    cameras: dict[str, CameraConfig] = field(
        default_factory=lambda: {
            "webcam": OpenCVCameraConfig(
                index_or_path=6,      # 摄像头索引或路径
                fps=30,                # 帧率
                width=640,             # 宽度（必须指定）
                height=480,            # 高度（必须指定）
                # color_mode=ColorMode.RGB,  # 颜色模式（默认 RGB）
                # rotation=Cv2Rotation.NO_ROTATION,  # 旋转（默认不旋转）
            ),
            # 可以添加多个摄像头
            # "wrist_camera": OpenCVCameraConfig(
            #     index_or_path=7,
            #     fps=30,
            #     width=640,
            #     height=480,
            # ),
        }
    )
```

#### 1.2 在 Robot 类中使用摄像头

```python
# src/lerobot/robots/ur5e/ur5e.py
from lerobot.cameras.utils import make_cameras_from_configs
from lerobot.errors import DeviceNotConnectedError
from ..robot import Robot
from .config_ur5e import UR5eConfig

class UR5eRobot(Robot):
    config_class = UR5eConfig
    name = "ur5e"
    
    def __init__(self, config: UR5eConfig):
        super().__init__(config)
        self.config = config
        
        # 从配置创建摄像头实例
        self.cameras = make_cameras_from_configs(config.cameras)
        
        # 其他初始化...
    
    @property
    def _cameras_ft(self) -> dict[str, tuple]:
        """定义摄像头特征（用于数据集）"""
        features = {}
        for cam_name in self.cameras:
            # 返回目标分辨率（用于数据集）
            # 注意：这里返回的分辨率应该与 get_observation 中返回的图像分辨率一致
            features[cam_name] = (480, 480, 3)  # (height, width, channels)
        return features
    
    @cached_property
    def observation_features(self):
        """定义观察特征"""
        return {
            **self._motors_ft,  # 关节特征
            **self._cameras_ft,  # 摄像头特征
        }
    
    def connect(self, calibrate: bool = True) -> None:
        """连接机器人所有设备"""
        # 连接机器人...
        
        # 连接摄像头
        print("Connecting cameras...")
        for cam_name, cam in self.cameras.items():
            try:
                cam.connect()
                print(f"Camera '{cam_name}' connected successfully")
            except Exception as e:
                print(f"Warning: Failed to connect camera '{cam_name}': {e}")
    
    def get_observation(self):
        """获取观察数据"""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        
        observation = {
            # 关节数据...
            "joint_1.pos": float(joints[0]),
            # ...
        }
        
        # 读取摄像头图像
        for cam_key, cam in self.cameras.items():
            try:
                if not cam.is_connected:
                    # 摄像头未连接，返回黑色图像
                    img = np.zeros((480, 480, 3), dtype=np.uint8)
                else:
                    # 异步读取图像（推荐，性能更好）
                    img = cam.async_read(timeout_ms=500)
                    
                    # 调整到目标分辨率（如果需要）
                    if img.shape[0] != 480 or img.shape[1] != 480:
                        img = cv2.resize(img, (480, 480))
                    
                    # 确保数据类型正确
                    img = img.astype(np.uint8)
                    
            except Exception as e:
                print(f"Warning: Failed to read camera '{cam_key}': {e}")
                img = np.zeros((480, 480, 3), dtype=np.uint8)
            
            observation[cam_key] = img
        
        return observation
    
    def disconnect(self):
        """断开连接"""
        # 断开摄像头
        for cam in self.cameras.values():
            try:
                cam.disconnect()
            except Exception as e:
                print(f"Error disconnecting camera: {e}")
        
        # 断开机器人...
```

---

### 示例 2：自定义摄像头实现（高级）

#### 2.1 创建摄像头配置类

```python
# src/lerobot/cameras/my_camera/configuration_my_camera.py
from dataclasses import dataclass
from ..configs import CameraConfig

@CameraConfig.register_subclass("my_camera")
@dataclass
class MyCameraConfig(CameraConfig):
    """自定义摄像头配置"""
    device_path: str  # 设备路径
    custom_param: int = 0  # 自定义参数
```

#### 2.2 创建摄像头实现类

```python
# src/lerobot/cameras/my_camera/camera_my_camera.py
import numpy as np
from typing import Any
from ..camera import Camera
from .configuration_my_camera import MyCameraConfig

class MyCamera(Camera):
    """自定义摄像头实现"""
    
    def __init__(self, config: MyCameraConfig):
        super().__init__(config)
        self.config = config
        self.device = None  # 你的摄像头设备对象
    
    @property
    def is_connected(self) -> bool:
        """检查摄像头是否连接"""
        return self.device is not None and self.device.is_open()
    
    @staticmethod
    def find_cameras() -> list[dict[str, Any]]:
        """查找可用摄像头"""
        # 实现查找逻辑
        cameras = []
        # ... 查找摄像头 ...
        return cameras
    
    def connect(self, warmup: bool = True) -> None:
        """连接摄像头"""
        # 打开摄像头设备
        self.device = open_camera_device(self.config.device_path)
        
        # 配置摄像头参数
        self.device.set_resolution(self.width, self.height)
        self.device.set_fps(self.fps)
        
        if warmup:
            # 预热：读取一帧并丢弃
            _ = self.read()
    
    def read(self, color_mode: ColorMode | None = None) -> np.ndarray:
        """同步读取一帧"""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        
        # 从设备读取图像
        frame = self.device.capture_frame()
        
        # 转换为 numpy 数组
        img = np.array(frame)
        
        # 处理颜色模式
        if color_mode == ColorMode.RGB:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        return img
    
    def async_read(self, timeout_ms: float = 200) -> np.ndarray:
        """异步读取一帧"""
        # 对于简单实现，可以直接调用 read()
        # 对于高性能需求，应该使用后台线程
        return self.read()
    
    def disconnect(self) -> None:
        """断开连接"""
        if self.device:
            self.device.close()
            self.device = None
```

#### 2.3 在 utils.py 中注册

```python
# src/lerobot/cameras/utils.py
def make_cameras_from_configs(camera_configs: dict[str, CameraConfig]) -> dict[str, Camera]:
    cameras = {}
    
    for key, cfg in camera_configs.items():
        if cfg.type == "opencv":
            from .opencv import OpenCVCamera
            cameras[key] = OpenCVCamera(cfg)
        
        elif cfg.type == "my_camera":  # 注册新类型
            from .my_camera.camera_my_camera import MyCamera
            cameras[key] = MyCamera(cfg)
        
        # ... 其他类型 ...
    
    return cameras
```

---

## 关键概念详解

### 1. 分辨率处理

**问题**：摄像头实际分辨率 vs 数据集目标分辨率

**解决方案**：
```python
# 配置中使用摄像头实际支持的分辨率
cameras = {
    "webcam": OpenCVCameraConfig(
        index_or_path=6,
        width=640,   # 摄像头实际分辨率
        height=480,
        fps=30,
    )
}

# observation_features 中使用目标分辨率（用于数据集）
def _cameras_ft(self) -> dict[str, tuple]:
    return {
        "webcam": (480, 480, 3)  # 目标分辨率
    }

# 在 get_observation 中调整分辨率
def get_observation(self):
    img = cam.async_read()  # 读取的是 640x480
    img = cv2.resize(img, (480, 480))  # 调整到 480x480
    return {"webcam": img}
```

### 2. 异步读取 vs 同步读取

**异步读取（推荐）**：
- 使用后台线程持续读取
- 返回最新的一帧
- 性能更好，不会阻塞主线程

**同步读取**：
- 每次调用时从摄像头读取
- 可能阻塞主线程
- 适合单次读取场景

### 3. 错误处理

**最佳实践**：
```python
def get_observation(self):
    for cam_key, cam in self.cameras.items():
        try:
            if not cam.is_connected:
                img = np.zeros((480, 480, 3), dtype=np.uint8)
                continue
            
            img = cam.async_read(timeout_ms=500)
            
        except TimeoutError:
            print(f"Timeout reading from camera '{cam_key}'")
            img = np.zeros((480, 480, 3), dtype=np.uint8)
        
        except Exception as e:
            print(f"Error reading camera '{cam_key}': {e}")
            img = np.zeros((480, 480, 3), dtype=np.uint8)
        
        observation[cam_key] = img
```

---

## 常见问题

### Q1: 摄像头索引不固定怎么办？

**A**: 使用设备路径而不是索引
```python
OpenCVCameraConfig(
    index_or_path="/dev/video6",  # 使用路径
    # ...
)
```

### Q2: 摄像头不支持指定的分辨率怎么办？

**A**: 配置中使用摄像头支持的分辨率，然

---
### Q2: 摄像头不支持指定的分辨率怎么办？

**A**: 配置中使用摄像头支持的分辨率，然后在 `get_observation` 中调整到目标分辨率
```python
# 配置中使用摄像头实际支持的分辨率（例如 640x480）
cameras = {
    "webcam": OpenCVCameraConfig(
        index_or_path=6,
        width=640,   # 摄像头实际支持的分辨率
        height=480,
        fps=30,
    )
}

# 在 get_observation 中调整到目标分辨率（480x480）
def get_observation(self):
    img = cam.async_read()  # 读取的是 640x480
    img = cv2.resize(img, (480, 480))  # 调整到目标分辨率
    return {"webcam": img}
```

### Q3: 摄像头连接失败怎么办？

**A**: 检查以下几点：
1. **权限问题**：
   ```bash
   sudo usermod -a -G video $USER
   # 然后重新登录或重启
   ```

2. **设备被占用**：
   ```bash
   # 检查是否有其他程序在使用摄像头
   lsof /dev/video6
   # 如果有，关闭占用摄像头的程序
   ```

3. **摄像头索引错误**：
   ```bash
   # 使用工具查找可用摄像头
   lerobot-find-cameras opencv
   ```

4. **使用设备路径而不是索引**：
   ```python
   OpenCVCameraConfig(
       index_or_path="/dev/video6",  # 使用路径更稳定
       # ...
   )
   ```

### Q4: 视频是黑色的怎么办？

**A**: 可能的原因和解决方案：

1. **摄像头未连接**：
   ```python
   # 在 get_observation 中检查连接状态
   if not cam.is_connected:
       print(f"Camera '{cam_key}' is not connected")
       img = np.zeros((480, 480, 3), dtype=np.uint8)
   ```

2. **读取超时**：
   ```python
   try:
       img = cam.async_read(timeout_ms=500)  # 增加超时时间
   except TimeoutError:
       print(f"Timeout reading from camera '{cam_key}'")
       img = np.zeros((480, 480, 3), dtype=np.uint8)
   ```

3. **摄像头需要预热**：
   ```python
   # 在 connect 中已经包含 warmup，确保足够时间
   cam.connect(warmup=True)  # 默认会预热 1 秒
   ```

4. **检查摄像头是否真的在工作**：
   ```python
   # 测试脚本
   import cv2
   cap = cv2.VideoCapture(6)
   ret, frame = cap.read()
   if ret:
       print(f"Camera works! Frame shape: {frame.shape}")
       cv2.imwrite("test_frame.jpg", frame)
   cap.release()
   ```

### Q5: 如何支持多个摄像头？

**A**: 在配置中定义多个摄像头：
```python
cameras: dict[str, CameraConfig] = field(
    default_factory=lambda: {
        "webcam": OpenCVCameraConfig(
            index_or_path=6,
            fps=30,
            width=640,
            height=480,
        ),
        "wrist_camera": OpenCVCameraConfig(
            index_or_path=7,
            fps=30,
            width=640,
            height=480,
        ),
    }
)
```

然后在 `get_observation` 中读取所有摄像头：
```python
def get_observation(self):
    observation = {}
    
    # 读取所有摄像头
    for cam_key, cam in self.cameras.items():
        img = cam.async_read()
        observation[cam_key] = img
    
    return observation
```

### Q6: 如何调试摄像头问题？

**A**: 使用以下调试技巧：

1. **打印摄像头信息**：
   ```python
   def connect(self):
       for cam_name, cam in self.cameras.items():
           print(f"Connecting camera: {cam_name}")
           print(f"  Config: {cam.config}")
           print(f"  Index/Path: {cam.config.index_or_path}")
           cam.connect()
           print(f"  Connected: {cam.is_connected}")
           print(f"  Resolution: {cam.width}x{cam.height}")
           print(f"  FPS: {cam.fps}")
   ```

2. **保存测试图像**：
   ```python
   def get_observation(self):
       for cam_key, cam in self.cameras.items():
           img = cam.async_read()
           
           # 保存第一帧用于调试
           if not hasattr(self, '_saved_first_frame'):
               cv2.imwrite(f"debug_{cam_key}.jpg", img)
               print(f"Saved debug image: debug_{cam_key}.jpg")
               self._saved_first_frame = True
   ```

3. **检查图像统计信息**：
   ```python
   def get_observation(self):
       for cam_key, cam in self.cameras.items():
           img = cam.async_read()
           print(f"Camera '{cam_key}': shape={img.shape}, dtype={img.dtype}, "
                 f"min={img.min()}, max={img.max()}, mean={img.mean():.2f}")
   ```

---

## 完整适配流程检查清单

### 步骤 1: 准备工作
- [ ] 确定摄像头类型（USB/网络/特殊驱动）
- [ ] 查找摄像头索引或路径
- [ ] 测试摄像头是否可以正常读取
- [ ] 确定摄像头支持的分辨率和 FPS

### 步骤 2: 配置摄像头
- [ ] 在 `RobotConfig` 中定义 `cameras` 字典
- [ ] 创建 `CameraConfig` 实例（如 `OpenCVCameraConfig`）
- [ ] 指定 `width`、`height`、`fps`（必须指定）
- [ ] 指定 `index_or_path`

### 步骤 3: 在机器人中使用
- [ ] 在 `__init__` 中使用 `make_cameras_from_configs()` 创建摄像头实例
- [ ] 实现 `_cameras_ft` 属性，定义摄像头特征
- [ ] 在 `observation_features` 中包含摄像头特征
- [ ] 在 `connect()` 中连接所有摄像头
- [ ] 在 `get_observation()` 中读取摄像头图像
- [ ] 在 `disconnect()` 中断开所有摄像头连接

### 步骤 4: 处理分辨率
- [ ] 配置中使用摄像头实际支持的分辨率
- [ ] `observation_features` 中使用目标分辨率（数据集需要的分辨率）
- [ ] 在 `get_observation()` 中调整图像到目标分辨率

### 步骤 5: 错误处理
- [ ] 检查摄像头连接状态
- [ ] 处理 `TimeoutError`
- [ ] 处理其他异常，返回黑色图像作为占位符
- [ ] 添加详细的错误日志

### 步骤 6: 测试
- [ ] 测试摄像头连接
- [ ] 测试图像读取
- [ ] 测试分辨率调整
- [ ] 测试错误处理
- [ ] 测试多摄像头（如果有）

---

## 实际案例：UR5e 摄像头适配

### 完整代码示例

```python
# src/lerobot/robots/ur5e/config_ur5e.py
from dataclasses import dataclass, field
from lerobot.cameras import CameraConfig
from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from ..config import RobotConfig

@RobotConfig.register_subclass("ur5e")
@dataclass
class UR5eConfig(RobotConfig):
    robot_ip: str = "192.168.31.2"
    
    cameras: dict[str, CameraConfig] = field(
        default_factory=lambda: {
            "webcam": OpenCVCameraConfig(
                index_or_path=6,  # 使用实际可用的摄像头索引
                fps=30,
                width=640,   # 摄像头实际支持的分辨率
                height=480,
            ),
        }
    )
```

```python
# src/lerobot/robots/ur5e/ur5e.py
from lerobot.cameras.utils import make_cameras_from_configs
from lerobot.errors import DeviceNotConnectedError
from ..robot import Robot
from .config_ur5e import UR5eConfig
import numpy as np
import cv2
from functools import cached_property

class UR5eRobot(Robot):
    config_class = UR5eConfig
    name = "ur5e"
    
    def __init__(self, config: UR5eConfig):
        super().__init__(config)
        self.config = config
        
        # 从配置创建摄像头实例
        self.cameras = make_cameras_from_configs(config.cameras)
        
        # 其他初始化...
    
    @property
    def _motors_ft(self) -> dict[str, type]:
        return {
            "joint_1.pos": float,
            "joint_2.pos": float,
            # ... 其他关节
        }
    
    @property
    def _cameras_ft(self) -> dict[str, tuple]:
        """定义摄像头特征（用于数据集）"""
        # 返回目标分辨率（480x480），而不是摄像头实际分辨率
        return {
            cam_name: (480, 480, 3)  # (height, width, channels)
            for cam_name in self.cameras
        }
    
    @cached_property
    def observation_features(self):
        return {
            **self._motors_ft,
            **self._cameras_ft,
        }
    
    def connect(self, calibrate: bool = True) -> None:
        """连接机器人所有设备""": 配置中使用摄像头支持的分辨率，然

        # 连接机器人...
        
        # 连接摄像头
        print("Connecting cameras...")
        for cam_name, cam in self.cameras.items():
            try:
                cam.connect()
                print(f"Camera '{cam_name}' connected successfully")
            except Exception as e:
                print(f"Warning: Failed to connect camera '{cam_name}': {e}")
                print("You may need to:")
                print("1. Check if the camera is connected")
                print("2. Check camera permissions (run: sudo usermod -a -G video $USER)")
                print("3. Make sure no other program is using the camera")
    
    def get_observation(self):
        """获取观察数据"""
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected.")
        
        # 获取关节数据
        observation = {
            "joint_1.pos": float(joints[0]),
            # ... 其他关节数据: 配置中使用摄像头支持的分辨率，然

                    img = cam.async_read(timeout_ms=500)
                    
                    # 调整到目标分辨率（480x480）
                    if img.shape[0] != 480 or img.shape[1] != 480:
                        img = cv2.resize(img, (480, 480))
                    
                    # 确保数据类型正确
                    img = img.astype(np.uint8)
                    
                except TimeoutError as e:
                    print(f"Warning: Timeout reading from camera '{cam_key}': {e}")
                    img = np.zeros((480, 480, 3), dtype=np.uint8)
                
            except Exception as e:
                print(f"Warning: Failed to read camera '{cam_key}': {e}")
                img = np.zeros((480, 480, 3), dtype=np.uint8)
            
            observation[cam_key] = img
        
        return observation
    
    def disconnect(self):
        """断开连接"""
        # 断开摄像头
        for cam in self.cameras.values():
            try:
                cam.disconnect()
            except Exception as e:
                print(f"Error disconnecting camera: {e}")
        
        # 断开机器人...
```

---

## 最佳实践总结

### 1. 使用现有的摄像头实现
- **优先使用** `OpenCVCamera`（适用于大多数 USB 摄像头）
- **无需重新实现**，直接使用 `make_cameras_from_configs()`

### 2. 配置管理
- **必须指定** `width`、`height`、`fps`（`RobotConfig` 要求）
- **使用摄像头实际支持的分辨率**，然后在代码中调整
- **使用设备路径**而不是索引（更稳定）

### 3. 分辨率处理
- **配置中**：使用摄像头实际支持的分辨率
- **observation_features 中**：使用数据集需要的目标分辨率
- **get_observation 中**：调整图像到目标分辨率

### 4. 错误处理
- **总是检查**摄像头连接状态
- **处理超时**：增加 `timeout_ms` 或返回黑色图像
- **记录错误**：使用详细的日志信息
- **优雅降级**：摄像头失败时返回黑色图像，不中断程序

### 5. 性能优化
- **使用异步读取**（`async_read()`）而不是同步读取（`read()`）
- **预热摄像头**：在 `connect()` 中使用 `warmup=True`
- **批量读取**：一次读取所有摄像头，而不是逐个读取

### 6. 调试技巧
- **保存测试图像**：在开发阶段保存第一帧用于检查
- **打印统计信息**：检查图像形状、数据类型、数值范围
- **使用工具**：`lerobot-find-cameras` 查找可用摄像头

---

## 参考资源

### LeRobot 源码
- 摄像头基类：`src/lerobot/cameras/camera.py`
- OpenCV 摄像头：`src/lerobot/cameras/opencv/camera_opencv.py`
- RealSense 摄像头：`src/lerobot/cameras/realsense/camera_realsense.py`
- 摄像头工具：`src/lerobot/cameras/utils.py`

### 示例机器人
- SO100 Follower：`src/lerobot/robots/so100_follower/so100_follower.py`
- LeKiwi：`src/lerobot/robots/lekiwi/lekiwi.py`

### 工具命令
```bash
# 查找可用摄像头
lerobot-find-cameras opencv
lerobot-find-cameras realsense

# 测试摄像头
python3 -c "import cv2; cap = cv2.VideoCapture(6); ret, frame = cap.read(); print(f'Success: {ret}, Shape: {frame.shape if ret else None}')"
```

---

## 总结

适配摄像头到 LeRobot 的核心流程：

1. **了解摄像头**：确定类型、索引、支持的分辨率
2. **配置摄像头**：在 `RobotConfig` 中定义摄像头配置
3. **创建实例**：使用 `make_cameras_from_configs()` 创建摄像头对象
4. **连接摄像头**：在 `connect()` 中连接所有摄像头
5. **读取图像**：在 `get_observation()` 中读取图像并调整分辨率
6. **错误处理**：处理连接失败、读取超时等情况
7. **测试验证**：确保摄像头正常工作

**关键点**：
- 使用现有的 `OpenCVCamera` 实现（大多数情况下）
- 配置中使用摄像头实际分辨率，代码中调整到目标分辨率
- 完善的错误处理，确保程序稳定运行
- 使用异步读取提高性能

遵循这个指南，你应该能够成功适配任何摄像头到 LeRobot 系统中！🎉