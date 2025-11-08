# Vision Pro Teleoperator 适配指南

本指南将帮助你为 Apple Vision Pro 创建 LeRobot 兼容的 teleoperator（遥操作器）。

## 📋 适配步骤概览

我已经为你创建了基础模板代码，你需要完成以下步骤：

### ✅ 步骤 1: 目录结构（已完成）

已创建：
- `src/lerobot/teleoperators/vision_pro/`
- `configuration_vision_pro.py` - 配置文件
- `vision_pro_teleop.py` - Teleoperator 实现
- `__init__.py` - 模块导出

### ✅ 步骤 2: 注册到工厂（已完成）

已在 `src/lerobot/teleoperators/utils.py` 中添加 Vision Pro 支持

### 🔧 步骤 3: 实现 Vision Pro SDK 集成（需要你完成）

你需要：

1. **安装/集成 Vision Pro SDK**
   - 根据 Apple Vision Pro 的实际 SDK 或 API 进行集成
   - 可能需要使用网络连接、USB 连接或其他方式

2. **实现连接逻辑** (`connect()` 方法)
   ```python
   # 在 vision_pro_teleop.py 中
   def connect(self, calibrate: bool = True) -> None:
       # TODO: 实现实际的 Vision Pro 连接
       # 例如：
       # - 使用 Vision Pro 的 SDK 连接
       # - 或通过网络 API 连接
       # - 或通过 USB/蓝牙连接
   ```

3. **实现数据获取** (`get_action()` 方法中的追踪数据获取)
   ```python
   # 获取 Vision Pro 的追踪数据
   hand_pose = self.vision_pro_client.get_hand_tracking()
   head_pose = self.vision_pro_client.get_head_tracking()
   eye_gaze = self.vision_pro_client.get_eye_tracking()
   ```

4. **实现坐标转换** (`_convert_vision_pro_to_robot_action()` 方法)
   - Vision Pro 坐标系 → 机器人坐标系
   - 手部位置 → 机器人关节角度（可能需要逆运动学）
   - 手指弯曲 → 夹爪位置

## 🎯 核心实现要点

### 1. 动作特征定义 (`action_features`)

根据你的机器人类型定义动作特征。例如，对于 UR5e：

```python
@property
def action_features(self) -> dict:
    return {
        "joint_1.pos": float,
        "joint_2.pos": float,
        "joint_3.pos": float,
        "joint_4.pos": float,
        "joint_5.pos": float,
        "joint_6.pos": float,
        "hand_pos": float,
    }
```

### 2. 坐标转换策略

Vision Pro 提供的数据格式可能包括：
- **手部追踪**: 位置 (x, y, z)、旋转 (四元数)、手指关节角度
- **头部追踪**: 头部位置和旋转
- **眼部追踪**: 视线方向

你需要将这些转换为机器人动作：

**方案 A: 直接位置控制**
- 手部位置 → 机器人末端执行器位置
- 使用逆运动学计算关节角度

**方案 B: 相对增量控制**
- 手部位置变化 → 机器人位置增量
- 更适合精细控制

**方案 C: 姿态映射**
- 手部姿态 → 机器人末端姿态
- 需要完整的 6DOF 控制

### 3. 校准流程

建议实现校准流程：
1. **初始位置校准**: 记录 Vision Pro 的初始手部位置作为"零点"
2. **坐标系对齐**: 确保 Vision Pro 坐标系与机器人坐标系对齐
3. **动作范围映射**: 设置 Vision Pro 动作范围到机器人动作范围的映射

### 4. 数据平滑

Vision Pro 的追踪数据可能有噪声，建议：
- 使用指数移动平均平滑
- 或使用卡尔曼滤波
- 已在模板中实现了基础平滑功能

## 📝 使用示例

### 在 record.py 中使用

```bash
python -m lerobot.record \
    --robot.type=ur5e \
    --robot.robot_ip=192.168.31.2 \
    --teleop.type=vision_pro \
    --teleop.ip_address=192.168.1.100 \
    --teleop.port=8080 \
    --teleop.use_hand_tracking=true \
    --teleop.scale_factor=0.1 \
    --teleop.smoothing_factor=0.5 \
    --dataset.repo_id=your_username/ur5e_dataset \
    --dataset.num_episodes=10
```

### 在代码中使用

```python
from lerobot.teleoperators.vision_pro import VisionProTeleop, VisionProTeleopConfig

# 创建配置
config = VisionProTeleopConfig(
    ip_address="192.168.1.100",
    port=8080,
    use_hand_tracking=True,
    scale_factor=0.1,
    smoothing_factor=0.5,
)

# 创建 teleoperator
teleop = VisionProTeleop(config)

# 连接
teleop.connect()

# 获取动作
action = teleop.get_action()
print(action)  # {'joint_1.pos': 0.1, 'joint_2.pos': 0.2, ...}

# 断开
teleop.disconnect()
```

## 🔍 需要实现的关键部分

### 1. Vision Pro SDK 集成

根据 Vision Pro 的实际 SDK，实现：

```python
# 示例：假设有 Vision Pro Python SDK
# from vision_pro_sdk import VisionProClient

class VisionProTeleop(Teleoperator):
    def connect(self, calibrate: bool = True) -> None:
        # 实际连接代码
        self.vision_pro_client = VisionProClient(
            ip=self.config.ip_address,
            port=self.config.port
        )
        self.vision_pro_client.connect()
```

### 2. 逆运动学（如果需要）

如果使用位置控制，需要逆运动学将末端位置转换为关节角度：

```python
def _convert_vision_pro_to_robot_action(self, hand_pose: dict) -> dict:
    # 获取目标位置
    target_position = hand_pose["position"]
    target_orientation = hand_pose["rotation"]
    
    # 使用逆运动学计算关节角度
    # 例如使用 ur_kinematics 库
    joint_angles = inverse_kinematics(
        target_position,
        target_orientation,
        self.robot_config
    )
    
    return {
        "joint_1.pos": joint_angles[0],
        "joint_2.pos": joint_angles[1],
        # ...
    }
```

### 3. 数据格式适配

根据 Vision Pro 实际返回的数据格式调整：

```python
def get_action(self) -> dict[str, Any]:
    # 获取 Vision Pro 原始数据
    raw_data = self.vision_pro_client.get_tracking_data()
    
    # 解析数据格式（根据实际 SDK 调整）
    hand_pose = {
        "position": np.array([
            raw_data.hand.position.x,
            raw_data.hand.position.y,
            raw_data.hand.position.z
        ]),
        "rotation": np.array([
            raw_data.hand.rotation.x,
            raw_data.hand.rotation.y,
            raw_data.hand.rotation.z,
            raw_data.hand.rotation.w
        ]),
        "fingers": [
            raw_data.hand.fingers.thumb,
            raw_data.hand.fingers.index,
            # ...
        ]
    }
    
    # 转换为机器人动作
    return self._convert_vision_pro_to_robot_action(hand_pose)
```

## 🚀 测试建议

1. **单元测试**: 测试坐标转换逻辑
2. **集成测试**: 测试与 Vision Pro 的实际连接
3. **端到端测试**: 测试完整的数据采集流程

## 📚 参考资源

- LeRobot Teleoperator 基类: `src/lerobot/teleoperators/teleoperator.py`
- 示例实现: `src/lerobot/teleoperators/gamepad/teleop_gamepad.py`
- 文档: `docs/source/integrate_hardware.mdx`

## ⚠️ 注意事项

1. **坐标系**: Vision Pro 可能使用右手坐标系，机器人可能使用不同的坐标系，需要转换
2. **单位**: 确保单位一致（米、弧度等）
3. **延迟**: Vision Pro 追踪可能有延迟，考虑使用预测或缓冲
4. **安全性**: 实现动作限制，防止机器人超出安全范围
5. **校准**: 建议实现校准流程，确保动作映射准确

## 🎉 完成后的使用

完成实现后，你就可以使用 Vision Pro 来控制机器人并采集数据了！

```bash
# 使用 Vision Pro 记录数据
python -m lerobot.record \
    --robot.type=ur5e \
    --teleop.type=vision_pro \
    --teleop.ip_address=YOUR_VISION_PRO_IP \
    ...
```

