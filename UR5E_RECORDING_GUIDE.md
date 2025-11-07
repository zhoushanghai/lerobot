# UR5e 数据采集指南

本指南介绍如何使用自定义的 UR5e 机器人采集 v2.1 格式的数据集。

## 📋 准备工作

### 1. 硬件准备

- ✅ UR5e 机器人已连接并正常工作
- ✅ UR5e 控制器设置为 **Remote Control** 模式
- ✅ RealSense 相机已连接（手腕相机）
- ✅ Orbbec 相机已连接（外部相机）
- ✅ 手部夹爪已连接并配置

### 2. 软件准备

#### 安装依赖

```bash
# 确保已安装所有依赖
pip install ur-rtde pyrealsense2 pyorbbecsdk pymodbus
```

#### 登录 HuggingFace

```bash
huggingface-cli login --token YOUR_TOKEN
```

或设置环境变量：

```bash
export HF_USERNAME="your_username"
```

## 🚀 使用方法

### 方法 1: 使用命令行（推荐）

```bash
lerobot-record \
    --robot.type=ur5e \
    --robot.robot_ip=192.168.31.2 \
    --robot.camera_id=0 \
    --robot.id=my_ur5e \
    --teleop.type=keyboard \
    --dataset.repo_id=your_username/ur5e_dataset \
    --dataset.num_episodes=10 \
    --dataset.single_task="Pick and place the object" \
    --dataset.fps=30 \
    --dataset.episode_time_s=60 \
    --display_data=true
```

### 方法 2: 使用 Python 脚本

#### 步骤 1: 修改配置

编辑 `examples/ur5e_record.py`，修改以下参数：

```python
# 机器人配置
ROBOT_IP = "192.168.31.2"  # 你的 UR5e IP 地址
CAMERA_ID = 0  # 外部相机 ID

# 数据集配置
HF_USERNAME = "your_username"  # 你的 HuggingFace 用户名
DATASET_NAME = "ur5e_pick_place_v2"  # 数据集名称
NUM_EPISODES = 10  # Episode 数量
FPS = 30  # 帧率
EPISODE_TIME_S = 60  # 每个 episode 的时长（秒）

# 任务描述
TASK_DESCRIPTION = "Pick and place the object"
```

#### 步骤 2: 运行脚本

```bash
python examples/ur5e_record.py
```

## 📊 数据结构

采集的数据包含以下内容：

### 观察 (Observations)
- `joint_1.pos` 到 `joint_6.pos`: 6 个关节的位置（弧度）
- `hand_pos`: 手部夹爪位置（归一化到 0-1）
- `webcam_rgb`: 外部相机图像 (480x480x3)
- `wrist_rgb`: 手腕相机图像 (480x480x3)

### 动作 (Actions)
- `joint_1.pos` 到 `joint_6.pos`: 目标关节位置（弧度）
- `hand_pos`: 目标手部位置（归一化到 0-1）

## 🎮 控制说明

### 键盘控制

使用键盘控制机器人：

- **关节控制**: 使用方向键或 WASD 控制关节运动
- **手部控制**: 使用特定按键控制手部开合
- **开始/停止**: 按特定键开始/停止采集

> 注意：具体的按键映射需要查看 `KeyboardTeleop` 的实现

## ⚙️ 配置说明

### UR5eConfig 参数

- `robot_ip` (str): UR5e 控制器 IP 地址，默认 "192.168.31.2"
- `camera_id` (int): 外部相机 ID，默认 0
- `id` (str): 机器人 ID，用于标识不同的机器人

### DatasetRecordConfig 参数

- `repo_id` (str): 数据集仓库 ID，格式为 `用户名/数据集名`
- `single_task` (str): 任务描述（必填）
- `num_episodes` (int): 要采集的 episode 数量
- `fps` (int): 采集帧率，默认 30
- `episode_time_s` (int/float): 每个 episode 的时长（秒）
- `reset_time_s` (int/float): episode 之间的重置时间（秒）
- `push_to_hub` (bool): 是否上传到 HuggingFace Hub
- `private` (bool): 是否创建私有数据集

## 🔧 故障排除

### 1. 连接问题

**问题**: 无法连接到 UR5e

```bash
# 检查网络连接
ping 192.168.31.2

# 检查控制器是否在 Remote Control 模式
# 在示教器上检查
```

**解决**: 
- 确认 IP 地址正确
- 确认控制器在 Remote Control 模式
- 检查防火墙设置

### 2. 相机问题

**问题**: 无法读取相机图像

**解决**:
- 检查相机连接
- 检查相机驱动是否正确安装
- 确认相机 ID 正确

### 3. 手部夹爪问题

**问题**: 无法控制手部夹爪

**解决**:
- 检查 Modbus 连接
- 确认手部夹爪 IP 地址和端口
- 检查 `demo_modbus.py` 中的配置

### 4. 导入错误

**问题**: `ModuleNotFoundError: No module named 'ur5e_lib'`

**解决**:
```bash
# 确保项目已安装
pip install -e .

# 或确保项目根目录在 Python 路径中
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## 📝 最佳实践

1. **首次使用**: 
   - 先用少量 episode（如 2-3 个）测试
   - 确认数据格式正确
   - 检查图像质量

2. **数据质量**:
   - 确保任务描述清晰准确
   - 每个 episode 完成完整的任务
   - 保持一致的起始位置

3. **安全**:
   - 始终确保机器人在安全位置开始
   - 使用较小的速度限制进行测试
   - 随时准备停止（Ctrl+C）

4. **数据管理**:
   - 定期备份数据集
   - 使用有意义的任务描述
   - 记录采集时的环境条件

## 📚 更多资源

- [LeRobot 数据采集文档](https://huggingface.co/docs/lerobot/il_robots)
- [UR5e 官方文档](https://www.universal-robots.com/products/ur5-robot/)
- [HuggingFace Hub 文档](https://huggingface.co/docs/hub)

## 💡 提示

- 数据集会自动保存到本地: `~/.cache/huggingface/lerobot/{repo_id}`
- 可以使用 `--resume=true` 继续之前的采集
- 可以使用 `--display_data=false` 关闭画面显示以提高性能

祝你数据采集顺利！🎉

