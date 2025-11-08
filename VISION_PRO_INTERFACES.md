# Vision Pro Teleoperator 需要适配的接口清单

## 📋 必须实现的抽象接口

根据 `Teleoperator` 基类，你需要实现以下 **8 个抽象接口**：

### 1. ✅ `action_features` (属性)
**类型**: `@property`  
**返回**: `dict`  
**说明**: 定义动作特征结构，必须与 `get_action()` 返回的字典键匹配

```python
@property
def action_features(self) -> dict:
    """
    返回动作特征字典。
    键名必须与 get_action() 返回的字典键完全匹配。
    值应该是类型（如 float）或形状元组。
    """
    return {
        "joint_1.pos": float,
        "joint_2.pos": float,
        # ... 根据你的机器人类型定义
    }
```

**当前状态**: ✅ 已实现（模板代码中已定义，需要根据你的机器人调整）

---

### 2. ✅ `feedback_features` (属性)
**类型**: `@property`  
**返回**: `dict`  
**说明**: 定义反馈特征结构（如果 Vision Pro 支持反馈）

```python
@property
def feedback_features(self) -> dict:
    """
    返回反馈特征字典。
    如果 Vision Pro 不支持反馈，返回空字典 {}。
    """
    return {}  # 或定义具体的反馈特征
```

**当前状态**: ✅ 已实现（返回空字典，可根据需要扩展）

---

### 3. ✅ `is_connected` (属性)
**类型**: `@property`  
**返回**: `bool`  
**说明**: 检查 Vision Pro 是否已连接

```python
@property
def is_connected(self) -> bool:
    """
    检查 Vision Pro 设备是否已连接。
    如果返回 False，调用 get_action() 或 send_feedback() 会抛出异常。
    """
    return self.vision_pro_client is not None and \
           self.vision_pro_client.is_connected()
```

**当前状态**: ⚠️ 需要实现 `vision_pro_client.is_connected()` 方法

---

### 4. ✅ `is_calibrated` (属性)
**类型**: `@property`  
**返回**: `bool`  
**说明**: 检查是否已校准

```python
@property
def is_calibrated(self) -> bool:
    """
    检查 Vision Pro 是否已校准。
    如果不需要校准，始终返回 True。
    """
    return True  # 或检查校准数据是否存在
```

**当前状态**: ✅ 已实现（返回 True，可根据需要扩展）

---

### 5. 🔧 `connect()` (方法)
**类型**: `def connect(calibrate: bool = True) -> None`  
**说明**: 连接到 Vision Pro 设备

```python
def connect(self, calibrate: bool = True) -> None:
    """
    建立与 Vision Pro 的连接。
    
    Args:
        calibrate: 如果为 True，连接后自动校准
    
    需要实现：
    1. 初始化 Vision Pro SDK 客户端
    2. 建立连接（网络/USB/蓝牙等）
    3. 如果 calibrate=True，调用 self.calibrate()
    """
    # TODO: 实现实际的连接逻辑
    # self.vision_pro_client = VisionProClient(...)
    # self.vision_pro_client.connect()
```

**当前状态**: ⚠️ **需要你实现** - 这是核心接口之一

---

### 6. 🔧 `disconnect()` (方法)
**类型**: `def disconnect() -> None`  
**说明**: 断开连接并清理资源

```python
def disconnect(self) -> None:
    """
    断开与 Vision Pro 的连接并清理资源。
    
    需要实现：
    1. 关闭 Vision Pro SDK 连接
    2. 清理资源
    3. 重置连接状态
    """
    if self.vision_pro_client:
        self.vision_pro_client.disconnect()
        self.vision_pro_client = None
```

**当前状态**: ⚠️ **需要你实现** - 需要实际的断开逻辑

---

### 7. 🔧 `get_action()` (方法) - **核心接口**
**类型**: `def get_action() -> dict[str, Any]`  
**说明**: 获取当前动作（这是最核心的方法）

```python
def get_action(self) -> dict[str, Any]:
    """
    从 Vision Pro 获取当前动作。
    
    返回的字典键必须与 action_features 中定义的键完全匹配。
    
    需要实现：
    1. 从 Vision Pro 获取追踪数据（手部/头部/眼部）
    2. 将追踪数据转换为机器人动作
    3. 应用平滑和限制
    4. 返回动作字典
    
    Returns:
        dict: 动作字典，例如：
        {
            "joint_1.pos": 0.1,
            "joint_2.pos": 0.2,
            ...
        }
    """
    # TODO: 1. 获取 Vision Pro 追踪数据
    hand_pose = self.vision_pro_client.get_hand_tracking()
    
    # TODO: 2. 转换为机器人动作
    action = self._convert_vision_pro_to_robot_action(hand_pose)
    
    # TODO: 3. 应用平滑和限制
    return action
```

**当前状态**: ⚠️ **需要你实现** - 这是最核心的接口

---

### 8. ✅ `send_feedback()` (方法)
**类型**: `def send_feedback(feedback: dict[str, Any]) -> None`  
**说明**: 向 Vision Pro 发送反馈（可选）

```python
def send_feedback(self, feedback: dict[str, Any]) -> None:
    """
    向 Vision Pro 发送反馈（如果支持）。
    
    Args:
        feedback: 反馈数据字典，结构应该匹配 feedback_features
    
    如果 Vision Pro 不支持反馈，可以留空（pass）。
    """
    # TODO: 如果 Vision Pro 支持反馈，实现反馈逻辑
    # 例如：力反馈、触觉反馈、视觉反馈等
    pass
```

**当前状态**: ✅ 已实现（留空，可根据需要扩展）

---

### 9. ✅ `calibrate()` (方法)
**类型**: `def calibrate() -> None`  
**说明**: 校准 Vision Pro 设备

```python
def calibrate(self) -> None:
    """
    校准 Vision Pro 设备。
    
    校准可能包括：
    - 记录初始手部位置作为零点
    - 设置坐标系转换参数
    - 设置动作范围映射
    
    如果不需要校准，可以留空（pass）。
    """
    # TODO: 实现校准逻辑
    # 例如：记录初始位置、设置转换参数等
    pass
```

**当前状态**: ⚠️ **需要你实现** - 建议实现校准流程

---

### 10. ✅ `configure()` (方法)
**类型**: `def configure() -> None`  
**说明**: 配置 Vision Pro 设备

```python
def configure(self) -> None:
    """
    配置 Vision Pro 设备。
    
    可能包括：
    - 设置追踪模式（手部/头部/眼部）
    - 设置更新率
    - 设置坐标系
    - 设置其他设备参数
    
    如果不需要配置，可以留空（pass）。
    """
    # TODO: 实现配置逻辑
    pass
```

**当前状态**: ✅ 已实现（留空，可根据需要扩展）

---

## 📊 接口实现状态总结

| 接口 | 类型 | 状态 | 优先级 |
|------|------|------|--------|
| `action_features` | 属性 | ✅ 已实现 | 高 |
| `feedback_features` | 属性 | ✅ 已实现 | 低 |
| `is_connected` | 属性 | ⚠️ 需完善 | 高 |
| `is_calibrated` | 属性 | ✅ 已实现 | 中 |
| `connect()` | 方法 | ⚠️ **需实现** | **最高** |
| `disconnect()` | 方法 | ⚠️ **需实现** | **最高** |
| `get_action()` | 方法 | ⚠️ **需实现** | **最高** |
| `send_feedback()` | 方法 | ✅ 已实现 | 低 |
| `calibrate()` | 方法 | ⚠️ 需实现 | 中 |
| `configure()` | 方法 | ✅ 已实现 | 低 |

## 🎯 核心需要实现的接口（按优先级）

### 🔴 最高优先级（必须实现）

1. **`connect()`** - 连接 Vision Pro
   - 初始化 Vision Pro SDK 客户端
   - 建立连接（网络/USB/蓝牙等）

2. **`disconnect()`** - 断开连接
   - 关闭连接
   - 清理资源

3. **`get_action()`** - 获取动作（核心）
   - 从 Vision Pro 获取追踪数据
   - 转换为机器人动作
   - 应用平滑和限制

### 🟡 中等优先级（建议实现）

4. **`is_connected`** - 完善连接检查
   - 实现 `vision_pro_client.is_connected()` 方法

5. **`calibrate()`** - 实现校准流程
   - 记录初始位置
   - 设置坐标系转换参数

### 🟢 低优先级（可选）

6. **`configure()`** - 设备配置（如果需要）
7. **`send_feedback()`** - 反馈功能（如果 Vision Pro 支持）

## 💡 实现建议

### 最小可行实现（MVP）

要实现一个可用的 Vision Pro teleoperator，至少需要：

1. ✅ `action_features` - 定义动作结构
2. ✅ `feedback_features` - 返回空字典
3. ⚠️ `is_connected` - 实现连接检查
4. ✅ `is_calibrated` - 返回 True
5. ⚠️ `connect()` - **实现连接逻辑**
6. ⚠️ `disconnect()` - **实现断开逻辑**
7. ⚠️ `get_action()` - **实现动作获取和转换**
8. ✅ `send_feedback()` - 留空
9. ✅ `calibrate()` - 可以留空或简单实现
10. ✅ `configure()` - 可以留空

### 完整实现

为了更好的用户体验，建议实现：

- 完整的校准流程
- 坐标系转换
- 动作平滑和限制
- 错误处理和重连机制
- 反馈功能（如果支持）

## 🔍 关键实现点

### 1. Vision Pro SDK 集成

你需要找到或创建 Vision Pro 的 Python SDK/API 接口：

```python
# 示例：假设的 Vision Pro SDK
class VisionProClient:
    def __init__(self, ip: str, port: int):
        # 初始化连接参数
        pass
    
    def connect(self):
        # 建立连接
        pass
    
    def is_connected(self) -> bool:
        # 检查连接状态
        pass
    
    def get_hand_tracking(self) -> dict:
        # 获取手部追踪数据
        pass
    
    def disconnect(self):
        # 断开连接
        pass
```

### 2. 数据格式转换

Vision Pro 返回的数据格式 → 机器人动作格式：

```python
# Vision Pro 数据格式（示例）
vision_pro_data = {
    "hand": {
        "position": [x, y, z],  # 米
        "rotation": [qx, qy, qz, qw],  # 四元数
        "fingers": [thumb, index, middle, ring, pinky]  # 0-1
    }
}

# 转换为机器人动作
robot_action = {
    "joint_1.pos": float,  # 弧度
    "joint_2.pos": float,
    # ...
}
```

### 3. 坐标系转换

Vision Pro 坐标系 → 机器人坐标系：

- 可能需要旋转矩阵或四元数转换
- 可能需要缩放（scale_factor）
- 可能需要偏移（calibration offset）

## 📝 检查清单

在实现完成后，确保：

- [ ] 所有 8 个抽象接口都已实现
- [ ] `action_features` 的键与 `get_action()` 返回的键匹配
- [ ] `connect()` 能成功连接 Vision Pro
- [ ] `get_action()` 能正确获取和转换数据
- [ ] `disconnect()` 能正确清理资源
- [ ] 错误处理完善（连接失败、数据获取失败等）
- [ ] 代码通过 linter 检查

