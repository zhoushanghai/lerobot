#!/usr/bin/env python
"""
UR5e 数据采集示例

使用自定义的 UR5e 机器人采集 v2.1 格式的数据集。

使用前准备：
1. 确保 UR5e 控制器已连接并设置为 Remote Control 模式
2. 确保相机已连接（RealSense 和 Orbbec）
3. 确保手部夹爪已连接
4. 登录 HuggingFace: huggingface-cli login
"""

import os
from lerobot.record import record, DatasetRecordConfig, RecordConfig
from lerobot.robots.ur5e import UR5eConfig, UR5eRobot
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleopConfig

# ========== 配置参数 ==========
# 机器人配置
ROBOT_IP = "192.168.31.2"  # 修改为你的 UR5e IP 地址
ROBOT_ID = "my_ur5e"
CAMERA_ID = 0  # 外部相机 ID（通常为 0）

# 数据集配置
HF_USERNAME = os.getenv("HF_USERNAME", "your_username")  # 从环境变量获取或修改这里
DATASET_NAME = "ur5e_pick_place_v2"  # 数据集名称
NUM_EPISODES = 10  # 要采集的 episode 数量
FPS = 30  # 采集帧率
EPISODE_TIME_S = 60  # 每个 episode 的时长（秒）
RESET_TIME_S = 10  # episode 之间的重置时间（秒）

# 任务描述
TASK_DESCRIPTION = "Pick and place the object"  # 修改为你的任务描述

# ========== 创建配置 ==========

# 机器人配置
robot_config = UR5eConfig(
    robot_ip=ROBOT_IP,
    camera_id=CAMERA_ID,
    id=ROBOT_ID,
)

# 遥操作配置（键盘控制）
teleop_config = KeyboardTeleopConfig()

# 数据集配置
dataset_config = DatasetRecordConfig(
    repo_id=f"{HF_USERNAME}/{DATASET_NAME}",
    single_task=TASK_DESCRIPTION,
    num_episodes=NUM_EPISODES,
    fps=FPS,
    episode_time_s=EPISODE_TIME_S,
    reset_time_s=RESET_TIME_S,
    push_to_hub=True,  # 设置为 False 只保存到本地
    private=False,  # 设置为 True 创建私有数据集
)

# 记录配置
record_config = RecordConfig(
    robot=robot_config,
    dataset=dataset_config,
    teleop=teleop_config,
    display_data=True,  # 显示相机画面
    play_sounds=True,  # 音频反馈
    resume=False,  # 是否继续之前的采集
)

# ========== 开始采集 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("UR5e 数据采集")
    print("=" * 60)
    print(f"机器人 IP: {ROBOT_IP}")
    print(f"数据集: {HF_USERNAME}/{DATASET_NAME}")
    print(f"Episodes: {NUM_EPISODES}")
    print(f"帧率: {FPS} FPS")
    print(f"每个 Episode 时长: {EPISODE_TIME_S} 秒")
    print(f"任务: {TASK_DESCRIPTION}")
    print("=" * 60)
    print("\n请确认:")
    print("1. UR5e 控制器处于 Remote Control 模式")
    print("2. 机器人处于安全的起始位置")
    print("3. 相机已连接并正常工作")
    print("4. 手部夹爪已连接")
    print("5. 已登录 HuggingFace (huggingface-cli login)")
    print("\n按 Enter 开始采集，或 Ctrl+C 取消...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n已取消")
        exit(0)
    
    try:
        # 开始采集
        print("\n开始采集数据...")
        dataset = record(record_config)
        print(f"\n采集完成！")
        print(f"数据集保存位置: {dataset.root}")
        print(f"HuggingFace 链接: https://huggingface.co/datasets/{HF_USERNAME}/{DATASET_NAME}")
    except KeyboardInterrupt:
        print("\n\n采集已中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

