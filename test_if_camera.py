#!/usr/bin/env python
"""
快速测试脚本：检查您的相机是否可以通过 OpenCV 访问
如果这个脚本能成功读取图像，说明您不需要自己实现相机类
"""

import cv2
import sys

def test_camera(index_or_path):
    """测试相机是否可用"""
    print(f"正在测试相机: {index_or_path}")
    
    # 尝试打开相机
    if isinstance(index_or_path, str):
        cap = cv2.VideoCapture(index_or_path)
    else:
        cap = cv2.VideoCapture(index_or_path)
    
    if not cap.isOpened():
        print(f"❌ 无法打开相机 {index_or_path}")
        cap.release()
        return False
    
    # 尝试读取一帧
    ret, frame = cap.read()
    
    if ret:
        print(f"✅ 相机 {index_or_path} 可用！")
        print(f"   分辨率: {frame.shape[1]}x{frame.shape[0]}")
        print(f"   通道数: {frame.shape[2]}")
        print(f"   数据类型: {frame.dtype}")
        cap.release()
        return True
    else:
        print(f"❌ 相机 {index_or_path} 打开成功但无法读取图像")
        cap.release()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("相机兼容性测试")
    print("=" * 50)
    print()
    
    # 方法1: 使用 LeRobot 工具查找相机
    print("方法1: 使用 LeRobot 工具查找相机")
    print("运行命令: lerobot-find-cameras opencv")
    print()
    
    # 方法2: 测试常见的相机索引
    print("方法2: 测试常见的相机索引 (0-10)")
    found = False
    for i in range(11):
        if test_camera(i):
            found = True
            print()
    
    if not found:
        print("\n未找到可用的相机索引，请尝试：")
        print("1. 运行: lerobot-find-cameras opencv")
        print("2. 检查相机是否已连接")
        print("3. 检查相机权限（Linux: sudo chmod 666 /dev/video*）")
    
    print()
    print("=" * 50)
    print("结论:")
    if found:
        print("✅ 您的相机可以通过 OpenCV 访问")
        print("   您不需要自己实现相机类，直接使用 OpenCVCamera 即可！")
    else:
        print("❌ 未找到可通过 OpenCV 访问的相机")
        print("   可能需要：")
        print("   1. 检查相机驱动")
        print("   2. 检查相机连接")
        print("   3. 或考虑自己实现相机类")
    print("=" * 50)

