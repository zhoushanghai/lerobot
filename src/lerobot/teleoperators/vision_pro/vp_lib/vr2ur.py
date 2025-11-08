import numpy as np
from scipy.spatial.transform import Rotation as R
from avp_stream import VisionProStreamer
import argparse 
from typing import * 
import time
from ur_math import *

T_vr_to_world_initial = None
T_robot_to_world_initial = None


# **********************************************************************
# 1. 标定函数：获取和存储基准姿态
# **********************************************************************

def calibrate_base_poses(vr_wrist_to_world_ref: np.ndarray, robot_to_world_ref: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    标定函数：获取VR手腕和机械手在参考姿态下的世界坐标系齐次变换矩阵。
    
    Args:
        vr_wrist_to_world_ref: np.ndarray, shape (4, 4)
            VR手腕到世界坐标系的初始（参考）齐次变换矩阵 (T_vr_to_world_initial)
        robot_to_world_ref: np.ndarray, shape (4, 4)  
            机械手到世界坐标系的初始（参考）齐次变换矩阵 (T_robot_to_world_initial)
    
    Returns:
        tuple[np.ndarray, np.ndarray]: 
            (T_vr_to_world_initial, T_robot_to_world_initial)
    """
    if vr_wrist_to_world_ref.shape != (4, 4) or robot_to_world_ref.shape != (4, 4):
        raise ValueError("Input matrices must be 4x4.")
    
    # 在基于增量变换的思路中，偏移矩阵（T_vr_to_robot）实际上不再直接用于每一步的计算
    # 最关键的是锁定这两个初始姿态 (T_vr_to_world_initial 和 T_robot_to_world_initial)
    
    print("--- 标定完成 ---")
    print("VR初始姿态和机械手初始姿态已锁定。")
    
    # 返回这两个基准矩阵，用于后续的实时计算
    return vr_wrist_to_world_ref, robot_to_world_ref

# **********************************************************************
# 2. 运动函数：计算机器人目标姿态（包含旋转和位移）
# **********************************************************************

def calculate_robot_target_pose(T_vr_to_world_current: np.ndarray) -> np.ndarray:

    # 1. 确保输入有效
    if not all(m.shape == (4, 4) for m in [T_vr_to_world_initial, T_robot_to_world_initial, T_vr_to_world_current]):
        raise ValueError("All input matrices must be 4x4.")
    
    # 2. 计算 VR 运动的增量矩阵 (Delta T_vr)
    # Delta T_vr = T_vr_to_world_initial^(-1) * T_vr_to_world_current
    # T_world_to_vr_initial = T_vr_to_world_initial^(-1)
    T_world_to_vr_initial = np.linalg.inv(T_vr_to_world_initial)
    # Delta T_vr: VR 相对初始姿态的变化量
    Delta_T_vr = T_world_to_vr_initial @ T_vr_to_world_current
    
    # 3. 将相同的增量应用到机器人初始姿态上
    # T_robot_to_world_target = T_robot_to_world_initial * Delta_T_vr
    T_robot_to_world_target = T_robot_to_world_initial @ Delta_T_vr
    
    return T_robot_to_world_target


def update_base_poses(vr_wrist_to_world_ref: np.ndarray, robot_to_world_ref: np.ndarray):
    global T_vr_to_world_initial, T_robot_to_world_initial
    T_vr_to_world_initial = vr_wrist_to_world_ref
    T_robot_to_world_initial = robot_to_world_ref



def transform_matrix_to_tcp_coords(transform_matrix):
    """
    将4x4齐次变换矩阵转换为TCP坐标 [xyz, rotation_vector]
    
    Args:
        transform_matrix: np.ndarray, shape (1, 4, 4) 或 (4, 4)
            # measured from ground frame
    
    Returns:
        list: [x, y, z, rx, ry, rz]，rx, ry, rz为旋转矢量分量（弧度）
    """
    # 确保输入是4x4矩阵
    if transform_matrix.shape == (1, 4, 4):
        matrix = transform_matrix[0]  # 去掉第一个维度
    elif transform_matrix.shape == (4, 4):
        matrix = transform_matrix
    else:
        raise ValueError(f"Expected shape (1,4,4) or (4,4), got {transform_matrix.shape}")
    
    # 提取位置 (xyz)
    xyz = matrix[:3, 3].tolist()

    # 提取旋转矩阵并转换为旋转矢量
    rotation_matrix = matrix[:3, :3]
    rotation = R.from_matrix(rotation_matrix)
    
    # 旋转矢量 (3,) 弧度
    rotvec = rotation.as_rotvec()
    
    return xyz + rotvec.tolist()


def limit_tcp_pose(tcp_pose_target, tcp_pose_current, max_step, rotation_step=0.1):
    """
    限制TCP运动
    Args:
        tcp_pose_target: 目标TCP姿态
        tcp_pose_current: 当前TCP姿态  
        max_step: 位置步进值 (xyz)
        rotation_step: 旋转步进值 (rx, ry, rz)
    """
    new_tcp_pose = limit_tcp_pose_with_step(tcp_pose_target, tcp_pose_current, max_step, rotation_step)
    new_tcp_pose = limit_tcp_pose_range(new_tcp_pose)
    return new_tcp_pose


def limit_tcp_pose_with_step(tcp_pose_target, tcp_pose_current, max_step=0.03, rotation_step=0.1):
    """
    限制TCP运动步长，位置和旋转使用不同的步进值
    
    Args:
        tcp_pose_target: 目标TCP姿态 [x, y, z, rx, ry, rz]
        tcp_pose_current: 当前TCP姿态 [x, y, z, rx, ry, rz]
        max_step: 位置步进值 (xyz)
        rotation_step: 旋转步进值 (rx, ry, rz)
    """
    new_tcp_pose = list(tcp_pose_current)
    
    # 处理位置 (x, y, z) - 使用较小的步进值
    for i in range(3):
        if i < len(tcp_pose_current) and i < len(tcp_pose_target):
            # 计算目标步长
            step = tcp_pose_target[i] - tcp_pose_current[i]
            
            # 限制步长绝对值不超过max_step
            if abs(step) > max_step:
                step = max_step if step > 0 else -max_step
            
            # 应用限制后的步长
            new_tcp_pose[i] = tcp_pose_current[i] + step
    
    # # 处理旋转 (rx, ry, rz) - 使用较大的步进值
    # for i in range(3, 6):
    #     if i < len(tcp_pose_current) and i < len(tcp_pose_target):
    #         # 计算目标步长
    #         step = tcp_pose_target[i] - tcp_pose_current[i]
            
    #         # 限制步长绝对值不超过rotation_step
    #         if abs(step) > rotation_step:
    #             step = rotation_step if step > 0 else -rotation_step
            
    #         # 应用限制后的步长
    #         new_tcp_pose[i] = tcp_pose_current[i] + step
    new_tcp_pose[3] = tcp_pose_target[3]
    new_tcp_pose[4] = tcp_pose_target[4]
    new_tcp_pose[5] = tcp_pose_target[5]
    
    return new_tcp_pose

# 限制TCP运动的范围
def limit_tcp_pose_range(tcp_pose):
    """
    限制TCP运动范围
    """
    # 位置范围限制
    range_x = [-0.2, 0.2]
    range_y = [-0.6, -0.3]
    range_z = [0.3, 0.6]
    
    if tcp_pose[0] < range_x[0]:
        tcp_pose[0] = range_x[0]
    if tcp_pose[0] > range_x[1]:
        tcp_pose[0] = range_x[1]
    if tcp_pose[1] < range_y[0]:
        tcp_pose[1] = range_y[0]
    if tcp_pose[1] > range_y[1]:
        tcp_pose[1] = range_y[1]
    if tcp_pose[2] < range_z[0]:
        tcp_pose[2] = range_z[0]
    if tcp_pose[2] > range_z[1]:
        tcp_pose[2] = range_z[1]
    
    # 旋转范围限制 (弧度)
    if len(tcp_pose) >= 6:
        rotation_range = [-3.14, 3.14]  # ±180度
        for i in range(3, 6):  # rx, ry, rz
            if tcp_pose[i] < rotation_range[0]:
                tcp_pose[i] = rotation_range[0]
            if tcp_pose[i] > rotation_range[1]:
                tcp_pose[i] = rotation_range[1]
    
    return tcp_pose


## 建立一个用来转化手指数据的类
class Fingur:
    """处理手指数据的类，将手指关节的变换矩阵转换为可读的姿态信息"""

    def __init__(self):
        self.joint_info = []
    
    def euler2finger_action(self, euler):
        """将欧拉角转换为手指动作值"""
        action = 1000
        if 50 < euler :
            action = 0

        if -180 < euler and euler < 0:
            action = int(1000 - (-euler/180)*1000) - 1
        return action
        
    def calculate_hand_actions(self,right_fingers, deg=True):
        
        fingur_actions = [1000, 1000, 1000, 1000, 1000, 400] 

        if right_fingers is None:
            print("错误：未提供手指数据")
            return None
            
        if right_fingers.shape != (25, 4, 4):
            print(f"警告：手指数据形状为 {right_fingers.shape}，期望 (25, 4, 4)")
            return None
        
        self.joint_info = []

        def cal_action(i):
            T = right_fingers[i]  # 获取第i个关节的变换矩阵
            info = extract_pose_info(T, deg=deg)
            print(
                f"关节 {i}: euler_zyx(deg) = "
                f"[{info['euler_zyx'][0]:.2f}, {info['euler_zyx'][1]:.2f}, {info['euler_zyx'][2]:.2f}], "
                f"angle = {info['angle']:.2f}°"
            )
            return  round(info['euler_zyx'][0], 2)
    
        # 计算手指的控制量 24 19 24 9
        action = cal_action(24)
        finger_action = self.euler2finger_action(action)
        fingur_actions[0] = finger_action

        action = cal_action(19)
        finger_action = self.euler2finger_action(action)
        fingur_actions[1] = finger_action

        action = cal_action(14)
        finger_action = self.euler2finger_action(action)
        fingur_actions[2] = finger_action

        action = cal_action(9)
        finger_action = self.euler2finger_action(action)
        fingur_actions[3] = finger_action
        
        # -40 - 40
        big_finger_matrix=compute_transform_matrix(right_fingers[4], right_fingers[2])
        info = extract_pose_info(big_finger_matrix, deg=deg)
        big_finger_angle = info['euler_zyx'][0]
        """将欧拉角转换为手指动作值"""
        action = 1000
        if big_finger_angle < -40 :
            action = 0
        if big_finger_angle > 40 :
            action = 1000
        if -40 <= big_finger_angle <= 40:
            action = int(1000 - (big_finger_angle + 40)/80.0*1000) - 1

        print(
            f"[{info['euler_zyx'][0]:.2f}, {info['euler_zyx'][1]:.2f}, {info['euler_zyx'][2]:.2f}], "
            f"angle = {info['angle']:.2f}°"
        )
        fingur_actions[4] = action


        # distance = matrix_distance(right_fingers[2], right_fingers[6])
        # if 0.03 < distance < 0.06:
        #      action = int(1000 - (distance - 0.03)/0.03*1000) - 1
        # print(action)
        # fingur_actions[5] = action
            
        return fingur_actions

    def print_info(self, deg=True):
        """
        打印所有手指关节的姿态信息
        
        Args:
            deg: bool, 是否使用角度制（默认True）
        """
        if not self.joint_info:
            self.process(deg=deg)
        
        print("\n" + "="*80)
        print("右手手指关节信息 (25个关节)")
        print("="*80)
        
        for i, info in enumerate(self.joint_info):
            print(f"\n关节 {i}:")
            print(f"  位置 (x, y, z): [{info['translation'][0]:.4f}, {info['translation'][1]:.4f}, {info['translation'][2]:.4f}]")
            if deg:
                print(f"  欧拉角 ZYX (yaw, pitch, roll): [{info['euler_zyx'][0]:.2f}°, {info['euler_zyx'][1]:.2f}°, {info['euler_zyx'][2]:.2f}°]")
            else:
                print(f"  欧拉角 ZYX (yaw, pitch, roll): [{info['euler_zyx'][0]:.4f}, {info['euler_zyx'][1]:.4f}, {info['euler_zyx'][2]:.4f}] rad")
            print(f"  旋转轴: [{info['axis'][0]:.4f}, {info['axis'][1]:.4f}, {info['axis'][2]:.4f}]")
            print(f"  旋转角度: {info['angle']:.2f}°" if deg else f"  旋转角度: {info['angle']:.4f} rad")
        
        print("\n" + "="*80)



class VRArmMapper:
    """
    VR 手腕坐标到机械臂末端坐标的映射工具类
    支持标定并计算当前 VR 相对于标定时的变化量，
    直接映射到机械臂坐标系中。
    """

    def __init__(self):
        self.T_arm_vr = None          # VR -> 机械臂坐标变换矩阵
        self.T_vr_hand_init = None    # 标定时 VR 手腕姿态
        self.T_vr_hand_init_invert = None    # 标定时 VR 手腕姿态
        self.T_arm_ee_init = None     # 标定时 机械臂末端姿态
        self.is_calibrated = False


    @staticmethod
    def invert_transform(T):
        """计算齐次变换矩阵的逆"""
        R = T[:3, :3]
        t = T[:3, 3]
        T_inv = np.eye(4)
        T_inv[:3, :3] = R.T
        T_inv[:3, 3] = -R.T @ t
        return T_inv

    def calibrate(self, T_vr_hand, T_arm_ee):
        """
        标定：根据一帧 VR 和机械臂末端的姿态计算映射矩阵
        参数:
            T_vr_hand: np.ndarray(4x4) VR 手腕姿态矩阵
            T_arm_ee:  np.ndarray(4x4) 机械臂末端姿态矩阵
        """
        # self.T_arm_vr = T_arm_ee @ self.invert_transform(T_vr_hand)
        self.T_vr_hand_init = T_vr_hand.copy()
        # print("--------------------------------")
        # print("self.T_vr_hand_init:\n", self.T_vr_hand_init)
        self.T_vr_hand_init_invert = self.invert_transform(self.T_vr_hand_init)
        # print("self.T_vr_hand_init_invert:\n", self.T_vr_hand_init_invert)
        # print("--------------------------------")
        self.T_arm_ee_init = T_arm_ee.copy()
        self.T_arm_ee_init_invert = self.invert_transform(self.T_arm_ee_init)
        self.is_calibrated = True
        # return self.T_vr_hand_init_invert
        return self.T_vr_hand_init

    def update(self, T_vr_hand_current):
        """
        根据当前 VR 姿态计算机械臂的新姿态（相对于初始标定）
        参数:
            T_vr_hand_current: np.ndarray(4x4) 当前 VR 手腕姿态矩阵
        返回:
            T_arm_ee_new: np.ndarray(4x4) 新的机械臂末端姿态
        """
        if not self.is_calibrated:
            raise RuntimeError("请先调用 calibrate() 进行标定！")

        # 当前 VR 相对于初始标定时的变化量
        delta_T_vr = self.T_vr_hand_init_invert @ T_vr_hand_current
        print("手在vr视图下的变化量：:\n", delta_T_vr)

        # 先计算转换
        T_arm = self.T_arm_ee_init @ delta_T_vr

        # 再在z轴方向平移-0.1
        T_translate_z = np.eye(4)
        T_translate_z[2, 3] = -0.1
        T_arm = T_arm @ T_translate_z

        print("机械臂在机械臂基底坐标系下的值:\n", T_arm)
        return T_arm

    def reset(self):
        """重置标定"""
        self.T_arm_vr = None
        self.T_vr_hand_init = None
        self.T_arm_ee_init = None
        self.is_calibrated = False




# def reorder_homogeneous(T_vp):
#     """将VR坐标系转换为机械臂坐标系：绕Z轴旋转180°，反向X和Y"""
#     Tz_180 = np.array([
#         [-1,  0,  0,  0],
#         [ 0, -1,  0,  0],
#         [ 0,  0,  1,  0],
#         [ 0,  0,  0,  1]
#     ])
#     T_converted = Tz_180 @ T_vp
#     # T_converted[0, 3] *= -1
#     # T_converted[1, 3] *= -1
#     return T_converted

def reorder_homogeneous(T_vp):
    """VR坐标系 -> 机械臂坐标系：合并旋转矩阵"""
    T_combined = np.array([
        [ 0,  0, -1, 0],
        [ 0, -1,  0, 0],
        [-1,  0,  0, 0],
        [ 0,  0,  0, 1]
    ])
    
    # 右乘局部旋转
    T_converted = T_vp @ T_combined
    return T_converted

# -----------------------------
# 使用示例
# -----------------------------
if __name__ == "__main__":
    mapper = VRArmMapper()

    # INSERT_YOUR_CODE
    # 测试 reorder_homogeneous
    import numpy as np

    # 构造一个VR坐标系下的齐次变换矩阵: X右/Y上/Z前
    T_vr = np.array([
        [1, 0, 0, 0.1],
        [0, 1, 0, 0.4],
        [0, 0, 1, 0.3],
        [0, 0, 0, 1]
    ])
    print("原始VR齐次矩阵:\n", T_vr)
    T_arm = reorder_homogeneous(T_vr)
    print("转换到机械臂坐标系的齐次矩阵:\n", T_arm)

