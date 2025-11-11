import numpy as np
import scipy.linalg as la

def se3_smooth_filter(current_pose, prev_filtered_pose=None, alpha=0.3):
    """
    SE(3)李代数空间低通平滑滤波
    
    Args:
        current_pose: 当前帧的4x4齐次变换矩阵
        prev_filtered_pose: 上一帧滤波后的位姿，如果为None则返回当前帧
        alpha: 平滑因子 (0.1-0.5)，越小越平滑
    
    Returns:
        filtered_pose: 滤波后的4x4齐次变换矩阵
    """
    
    if prev_filtered_pose is None:
        return current_pose.copy()
    
    # 1. 计算相对变换: T_delta = T_prev^{-1} * T_curr
    T_delta = la.inv(prev_filtered_pose) @ current_pose
    
    # 2. 将相对变换映射到李代数 (se(3)空间)
    R = T_delta[:3, :3]
    t = T_delta[:3, 3]
    
    # 计算旋转部分的对数映射
    cos_theta = (np.trace(R) - 1) / 2
    cos_theta = np.clip(cos_theta, -1, 1)
    theta = np.arccos(cos_theta)
    
    if theta < 1e-10:
        # 无旋转或极小旋转
        phi = np.zeros(3)
        rho = t
    else:
        # 计算旋转轴
        axis = np.array([R[2,1]-R[1,2], R[0,2]-R[2,0], R[1,0]-R[0,1]])
        axis = axis / (2 * np.sin(theta))
        phi = theta * axis
        
        # 计算平移部分
        axis_hat = np.array([[0, -axis[2], axis[1]],
                           [axis[2], 0, -axis[0]],
                           [-axis[1], axis[0], 0]])
        
        V_inv = (np.eye(3) - 0.5 * axis_hat + 
                (1 - (theta * np.cos(theta/2)) / (2 * np.sin(theta/2))) / (theta**2) * axis_hat @ axis_hat)
        rho = V_inv @ t
    
    xi_delta = np.concatenate([rho, phi])
    
    # 3. 在李代数空间进行低通滤波
    xi_filtered_delta = alpha * xi_delta
    
    # 4. 将滤波后的李代数映射回李群 (SE(3)空间)
    rho_f = xi_filtered_delta[:3]
    phi_f = xi_filtered_delta[3:]
    theta_f = la.norm(phi_f)
    
    if theta_f < 1e-10:
        # 无旋转的情况
        T_filtered_delta = np.eye(4)
        T_filtered_delta[:3, 3] = rho_f
    else:
        # 有旋转的情况
        axis_f = phi_f / theta_f
        axis_f_hat = np.array([[0, -axis_f[2], axis_f[1]],
                             [axis_f[2], 0, -axis_f[0]],
                             [-axis_f[1], axis_f[0], 0]])
        
        # Rodrigues公式计算旋转矩阵
        R_f = (np.eye(3) + np.sin(theta_f) * axis_f_hat + 
               (1 - np.cos(theta_f)) * axis_f_hat @ axis_f_hat)
        
        # 计算平移部分
        V = (np.eye(3) + (1 - np.cos(theta_f)) / (theta_f**2) * axis_f_hat +
             (theta_f - np.sin(theta_f)) / (theta_f**3) * axis_f_hat @ axis_f_hat)
        
        t_f = V @ rho_f
        
        T_filtered_delta = np.eye(4)
        T_filtered_delta[:3, :3] = R_f
        T_filtered_delta[:3, 3] = t_f
    
    # 5. 组合全局位姿
    filtered_pose = prev_filtered_pose @ T_filtered_delta
    
    return filtered_pose

# 使用示例
class SE3Smoother:
    """简单的SE(3)平滑器封装类"""
    
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.prev_filtered = None
    
    def smooth_pose(self, current_pose):
        """平滑当前位姿"""
        smoothed = se3_smooth_filter(current_pose, self.prev_filtered, self.alpha)
        self.prev_filtered = smoothed.copy()
        return smoothed

# 测试示例
if __name__ == "__main__":
    # 创建平滑器
    smoother = SE3Smoother(alpha=0.2)
    
    # 模拟测试数据
    current_pose = np.eye(4)
    
    print("帧号 | 原始位移 | 平滑后位移")
    print("-" * 40)
    
    for i in range(15):
        # 添加带噪声的运动
        noise_trans = 0.1 * np.random.randn(3)
        noise_rot = 0.05 * np.random.randn(3)
        
        # 创建增量变换
        delta_pose = np.eye(4)
        delta_pose[:3, 3] = [0.1, 0.05, 0.02] + noise_trans
        
        # 添加小旋转
        if la.norm(noise_rot) > 0.01:
            axis = noise_rot / la.norm(noise_rot)
            angle = 0.1
            axis_hat = np.array([[0, -axis[2], axis[1]],
                               [axis[2], 0, -axis[0]],
                               [-axis[1], axis[0], 0]])
            delta_pose[:3, :3] = (np.eye(3) + np.sin(angle) * axis_hat + 
                                (1 - np.cos(angle)) * axis_hat @ axis_hat)
        
        current_pose = current_pose @ delta_pose
        
        # 应用平滑
        smoothed_pose = smoother.smooth_pose(current_pose)
        
        print(f"{i:2d}  | [{current_pose[0,3]:.3f}, {current_pose[1,3]:.3f}, {current_pose[2,3]:.3f}] | "
              f"[{smoothed_pose[0,3]:.3f}, {smoothed_pose[1,3]:.3f}, {smoothed_pose[2,3]:.3f}]")