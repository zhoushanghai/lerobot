# UR5e 机器人集成指南

本指南将帮助你将自己的 UR5e 机器人集成到 LeRobot 框架中，以便采集 v2.1 格式的数据集。

## 📋 前置要求

1. **UR5e 机器人** - 已连接并可以访问控制器
2. **Python 环境** - 已安装 LeRobot (v2.1 版本)
3. **网络连接** - 机器人控制器和电脑在同一网络

## 🔧 安装依赖

UR5e 需要安装通信库，选择其中一个：

### 选项 1: ur_rtde (推荐)
```bash
pip install ur-rtde
```

### 选项 2: urx (备选)
```bash
pip install urx
```

## 📁 文件结构

我已经为你创建了以下文件：

```
src/lerobot/robots/ur5e/
├── __init__.py          # 导出配置和机器人类
├── config_ur5e.py       # UR5e 配置类
├── ur5e.py              # UR5e 机器人实现
└── README.md            # 详细文档

examples/
└── ur5e_record_example.py  # 使用示例
```

## 🚀 快速开始

### 1. 配置机器人 IP 地址

首先，找到你的 UR5e 控制器 IP 地址：
- 在机器人示教器上查看网络设置
- 或使用网络扫描工具查找

### 2. 设置机器人控制器

1. 将机器人控制器设置为 **Remote Control** 模式
2. 确保控制器和电脑在同一网络
3. 测试连接：`ping <机器人IP>`

### 3. 使用命令行采集数据

```bash
lerobot-record \
    --robot.type=ur5e \
    --robot.ip_address=192.168.1.100 \
    --robot.id=my_ur5e \
    --robot.cameras='{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}' \
    --teleop.type=keyboard \
    --dataset.repo_id=your_username/ur5e_dataset \
    --dataset.num_episodes=5 \
    --dataset.single_task="Pick and place the object" \
    --dataset.fps=30 \
    --dataset.episode_time_s=60 \
    --display_data=true
```

### 4. 或使用 Python API

```python
from lerobot.record import record, RecordConfig, DatasetRecordConfig
from lerobot.robots.ur5e import UR5eConfig
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleopConfig

# 配置机器人
robot_config = UR5eConfig(
    ip_address="192.168.1.100",  # 你的机器人IP
    id="my_ur5e",
    cameras={...},  # 相机配置
    max_joint_velocity=1.0,
    max_joint_acceleration=1.0,
)

# 配置数据集
dataset_config = DatasetRecordConfig(
    repo_id="your_username/ur5e_dataset",
    single_task="Pick and place",
    num_episodes=5,
    fps=30,
)

# 开始采集
record_config = RecordConfig(
    robot=robot_config,
    dataset=dataset_config,
    teleop=KeyboardTeleopConfig(),
    display_data=True,
)

dataset = record(record_config)
```

## 🎮 遥操作选项

### 键盘控制 (Keyboard)

最简单的选项，使用键盘控制机器人：

```bash
--teleop.type=keyboard
```

键盘控制说明：
- 使用方向键或 WASD 控制关节
- 具体按键映射需要查看 KeyboardTeleop 实现

### 自定义遥操作

如果你有其他遥操作设备（如游戏手柄、另一个机械臂等），可以：
1. 参考 `src/lerobot/teleoperators/` 中的示例
2. 实现自己的 Teleoperator 类

## ⚙️ 配置参数说明

### UR5eConfig 参数

- `ip_address` (str): 机器人控制器 IP 地址
- `rtde_port` (int): RTDE 通信端口，默认 30004
- `command_port` (int): 命令端口，默认 30002
- `max_joint_velocity` (float): 最大关节速度 (rad/s)，默认 1.0
- `max_joint_acceleration` (float): 最大关节加速度 (rad/s²)，默认 1.0
- `max_relative_target` (float): 每步最大相对目标变化 (rad)，默认 0.1
- `cameras` (dict): 相机配置字典
- `use_degrees` (bool): 是否使用度数而非弧度，默认 False

### 安全建议

1. **首次使用**：设置较小的 `max_joint_velocity` (如 0.5 rad/s)
2. **测试运动**：先用小的 `max_relative_target` (如 0.05 rad) 测试
3. **逐步增加**：确认安全后逐步增加速度和加速度限制

## 🔍 关节名称

UR5e 有 6 个自由度：

- `base_joint` - 基座旋转
- `shoulder_joint` - 肩部升降
- `elbow_joint` - 肘部弯曲
- `wrist_1_joint` - 腕部 1 旋转
- `wrist_2_joint` - 腕部 2 旋转
- `wrist_3_joint` - 腕部 3 旋转

## 🐛 故障排除

### 连接问题

**问题**: 无法连接到机器人
- 检查 IP 地址是否正确
- 确认机器人控制器在 Remote Control 模式
- 测试网络连接: `ping <机器人IP>`
- 检查防火墙设置

**问题**: 导入错误
```bash
# 安装 ur_rtde
pip install ur-rtde

# 或安装 urx
pip install urx
```

### 运动问题

**问题**: 机器人不移动
- 检查是否在 Remote Control 模式
- 确认安全停止按钮未按下
- 检查关节限位

**问题**: 运动不流畅
- 降低 `max_joint_velocity`
- 降低 `max_joint_acceleration`
- 增加控制频率（如果使用 RTDE）

## 📝 自定义修改

如果需要修改实现以适应你的特定需求：

1. **修改关节映射**: 编辑 `ur5e.py` 中的 `JOINT_NAMES`
2. **添加传感器**: 在 `get_observation()` 中添加传感器读取
3. **修改控制模式**: 在 `send_action()` 中修改控制命令
4. **添加安全限制**: 在 `send_action()` 中添加额外的安全检查

## 📚 更多资源

- [LeRobot 硬件集成文档](https://huggingface.co/docs/lerobot/integrate_hardware)
- [UR5e 官方文档](https://www.universal-robots.com/products/ur5-robot/)
- [ur_rtde 文档](https://sdurobotics.gitlab.io/ur_rtde/)

## 💡 提示

1. **首次使用**：建议先用示教器手动控制机器人到安全位置
2. **测试连接**：先用简单的 Python 脚本测试连接，再使用完整的数据采集流程
3. **数据质量**：确保任务描述清晰，每个 episode 都完成完整的任务
4. **相机设置**：确保相机能清晰看到操作区域

## 🆘 需要帮助？

如果遇到问题：
1. 查看 `src/lerobot/robots/ur5e/README.md` 获取详细文档
2. 检查其他机器人实现作为参考（如 `so100_follower`）
3. 在 LeRobot Discord 社区寻求帮助

祝你数据采集顺利！🎉

