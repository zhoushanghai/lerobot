import numpy as np

def clamp(x, lo=-1.0, hi=1.0):
    return np.minimum(np.maximum(x, lo), hi)

def translation_from_T(T):
    """返回 (tx, ty, tz)"""
    return T[:3, 3].copy()

def rotation_matrix_from_T(T):
    return T[:3, :3].copy()


def euler_from_matrix_zyx(R):
    """
    Return (rz, ry, rx) in radians for intrinsic rotations around z, then y, then x (zyx),
    i.e. yaw (z), pitch (y), roll (x). This is one of the most commonly used orders.
    """
    sy = -R[0,2]
    sy = clamp(sy)
    ry = np.arcsin(sy)   # pitch
    cy = np.cos(ry)
    if np.abs(cy) > 1e-6:
        rz = np.arctan2(R[0,1] / cy, R[0,0] / cy)  # yaw
        rx = np.arctan2(R[1,2] / cy, R[2,2] / cy)  # roll
    else:
        # gimbal lock
        rz = 0.0
        rx = np.arctan2(-R[2,1], R[1,1])
    return np.array([rz, ry, rx])

def axis_angle_from_matrix(R):
    """
    Return (axis (3,), angle) where angle in radians, axis is unit vector.
    Handles near-zero rotation robustly.
    """
    # compute angle
    tr = np.trace(R)
    cos_theta = (tr - 1.0) / 2.0
    cos_theta = clamp(cos_theta)
    theta = np.arccos(cos_theta)
    if np.isclose(theta, 0.0):
        # no rotation: axis arbitrary (return x axis)
        return np.array([1.0, 0.0, 0.0]), 0.0
    if np.isclose(theta, np.pi):
        # angle ~ 180 deg: special handling to avoid division by zero
        # find axis from diagonal elements
        Rplus = (R + np.eye(3)) / 2.0
        axis = np.array([np.sqrt(clamp(Rplus[0,0])), np.sqrt(clamp(Rplus[1,1])), np.sqrt(clamp(Rplus[2,2]))])
        # signs disambiguation from off-diagonals
        if R[0,1] < 0: axis[1] = -axis[1]
        if R[0,2] < 0: axis[2] = -axis[2]
        axis = axis / (np.linalg.norm(axis) + 1e-12)
        return axis, theta
    # general case
    denom = 2.0 * np.sin(theta)
    axis = np.array([
        (R[2,1] - R[1,2]) / denom,
        (R[0,2] - R[2,0]) / denom,
        (R[1,0] - R[0,1]) / denom
    ])
    axis = axis / (np.linalg.norm(axis) + 1e-12)
    return axis, theta

def extract_pose_info(T, deg=True):
    """
    Given 4x4 homogeneous T, return:
      - translation (tx,ty,tz)
      - euler_xyz (rx,ry,rz) in degrees (if deg=True) or radians
      - euler_zyx (yaw, pitch, roll) in degrees (if deg=True) or radians
      - axis, angle (axis unit vector, angle)
    """
    if T.shape != (4,4):
        raise ValueError("T must be 4x4")
    t = translation_from_T(T)
    R = rotation_matrix_from_T(T)
    e_zyx = euler_from_matrix_zyx(R)
    axis, angle = axis_angle_from_matrix(R)
    if deg:
        e_zyx = np.degrees(e_zyx)
        angle = np.degrees(angle)
    return {
        "translation": t,
        "euler_zyx": e_zyx,    # [yaw(z), pitch(y), roll(x)]
        "axis": axis,
        "angle": angle
    }


def matrix_distance(T1, T2):

    if T1.shape != (4, 4) or T2.shape != (4, 4):
        raise ValueError("T1 and T2 must be 4x4 matrices")

    # 计算相对变换
    T1_inv = np.linalg.inv(T1)
    Delta = T1_inv @ T2

    # 平移距离
    t_delta = translation_from_T(Delta)
    t_dist = np.linalg.norm(t_delta)

    
    return t_dist

def compute_transform_matrix(T1, T2):
    """
    计算两个坐标系之间的变换矩阵，以T2作为基底
    
    即：计算 T1 到 T2 的变换矩阵
    变换矩阵 T_transform 满足：T2 = T1 @ T_transform
    
    Args:
        T1: np.ndarray, shape (4,4) - 第一个坐标系
        T2: np.ndarray, shape (4,4) - 第二个坐标系（作为基底）
    
    Returns:
        np.ndarray: 从T1到T2的变换矩阵 T_transform
    """
    if T1.shape != (4, 4) or T2.shape != (4, 4):
        raise ValueError("T1 and T2 must be 4x4 matrices")
    
    # T2 = T1 @ T_transform
    # 所以 T_transform = inv(T1) @ T2
    T1_inv = np.linalg.inv(T1)
    T_transform = T1_inv @ T2
    
    return T_transform


    # INSERT_YOUR_CODE
def rotation_vector_to_matrix(pose):
    """
    将 [x, y, z, rx, ry, rz] (其中 rx,ry,rz为旋转矢量) 转换为 4x4 齐次变换矩阵
    Args:
        pose: list or np.ndarray, 长度为6, [x, y, z, rx, ry, rz]
    Returns:
        T: np.ndarray, 4x4 齐次变换矩阵
    """
    pose = np.asarray(pose)
    if pose.shape != (6,):
        raise ValueError("输入必须是形状为(6,)的数组或列表")
    xyz = pose[:3]
    rvec = pose[3:6]
    rotation_norm = np.linalg.norm(rvec)
    if rotation_norm == 0:
        R = np.eye(3)
    else:
        # 将旋转矢量转为旋转矩阵
        from scipy.spatial.transform import Rotation as R_
        R = R_.from_rotvec(rvec).as_matrix()
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = xyz
    return T

