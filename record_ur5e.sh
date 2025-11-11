#!/bin/bash
# UR5e 数据采集脚本
# 激活虚拟环境（如果存在）
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
# 添加项目路径到 Python 路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
# 临时取消设置 ALL_PROXY，因为 socks:// 协议不被 httpx 支持
# 而且本地记录不需要访问 Hugging Face Hub
unset ALL_PROXY
unset all_proxy
# 方式2: 使用自定义路径（推荐，方便管理）
DATASET_DIR="$(pwd)/datasets/ur5e_dataset"

# 如果 resume=false 且数据集目录已存在，则删除旧数据集
if [ -d "$DATASET_DIR" ]; then
    echo "检测到已存在的数据集目录: $DATASET_DIR"
    echo "正在删除旧数据集..."
    rm -rf "$DATASET_DIR"
    echo "旧数据集已删除"
fi

# 运行记录脚本
# python3 -m lerobot.record \
#     --robot.type=ur5e \
#     --robot.robot_ip=192.168.31.2 \
#     --robot.id=my_ur5e \
#     --teleop.type=vision_pro \
#     --teleop.mode=visionpro \
#     --dataset.repo_id=your_username/ur5e_dataset \
#     --dataset.root="$DATASET_DIR" \
#     --dataset.num_episodes=100 \
#     --dataset.single_task="Pick and place the object" \
#     --dataset.fps=30 \
#     --dataset.episode_time_s=60 \
#     --dataset.push_to_hub=false \
#     --display_data=true \
#     --resume=false
python3 -m lerobot.record \
    --robot.type=ur5e \
    --robot.robot_ip=192.168.31.2 \
    --teleop.type=vision_pro \
    --teleop.mode=playback \
    --teleop.recording_file=pkl/new.pkl \
    --dataset.repo_id=your_username/ur5e_dataset \
    --dataset.root="$(pwd)/datasets/ur5e_dataset" \
    --dataset.num_episodes=100 \
    --dataset.single_task="Pick and place the object" \
    --dataset.fps=30 \
    --dataset.episode_time_s=60 \
    --dataset.reset_time_s=30 \
    --dataset.push_to_hub=false \
    --display_data=true \
    --resume=false


    # playback visionpro

    # 列出所有视频设备
    # v4l2-ctl --list-devices