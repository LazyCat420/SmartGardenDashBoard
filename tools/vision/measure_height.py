import cv2
import numpy as np
import os
import argparse
from pydantic import BaseModel
import structlog

log = structlog.get_logger()

class CameraIntrinsics(BaseModel):
    camera_matrix: list[list[float]]
    dist_coeffs: list[list[float]]

class CameraExtrinsics(BaseModel):
    rvec: list[list[float]]
    tvec: list[list[float]]

class HeightEstimator:
    def __init__(self, config_dir: str = "tools/vision/config"):
        intr_path = os.path.join(config_dir, "intrinsics.json")
        extr_path = os.path.join(config_dir, "extrinsics.json")
        
        if not os.path.exists(intr_path) or not os.path.exists(extr_path):
            log.error("missing_calibration_files")
            raise FileNotFoundError("Calibration files missing. Run calibrate_camera.py first.")
            
        with open(intr_path, "r") as f:
            intr = CameraIntrinsics.model_validate_json(f.read())
            
        with open(extr_path, "r") as f:
            extr = CameraExtrinsics.model_validate_json(f.read())
            
        self.mtx = np.array(intr.camera_matrix)
        self.dist = np.array(intr.dist_coeffs)
        self.rvec = np.array(extr.rvec)
        self.tvec = np.array(extr.tvec)
        
        # Calculate derived matrices
        # R is the 3x3 rotation matrix from camera to world
        self.R, _ = cv2.Rodrigues(self.rvec)
        
        # P is the 3x4 projection matrix: K * [R | t]
        Rt = np.hstack((self.R, self.tvec))
        self.P = np.dot(self.mtx, Rt)
        
        # H is the 3x3 homography matrix for the Z=0 plane: K * [R_col0, R_col1, tvec]
        H_components = np.hstack((self.R[:, 0:1], self.R[:, 1:2], self.tvec))
        self.H = np.dot(self.mtx, H_components)
        self.H_inv = np.linalg.inv(self.H)
        
        log.info("height_estimator_initialized")

    def get_ground_coordinates(self, pixel_u: float, pixel_v: float) -> tuple[float, float]:
        """
        Calculates the real-world (X, Y) coordinates of a pixel on the ground (Z=0).
        """
        # We need to undistort the pixel first
        # cv2.undistortPoints expects an array of shape (N, 1, 2)
        pts = np.array([[[pixel_u, pixel_v]]], dtype=np.float32)
        # Using P=self.mtx maps it back to pixel coordinates but undistorted
        undistorted = cv2.undistortPoints(pts, self.mtx, self.dist, P=self.mtx)
        u_un, v_un = undistorted[0][0]
        
        p = np.array([u_un, v_un, 1.0])
        p_world = np.dot(self.H_inv, p)
        
        # Normalize
        p_world = p_world / p_world[2]
        
        X = p_world[0]
        Y = p_world[1]
        return X, Y

    def calculate_height(self, top_pixel: tuple[float, float], bottom_pixel: tuple[float, float]) -> float:
        """
        Calculates the real-world height (Z) of an object.
        Assumes the object grows straight up vertically (same X,Y coordinates).
        """
        u_b, v_b = bottom_pixel
        u_t, v_t = top_pixel
        
        # 1. Find the X, Y coordinates on the ground
        X, Y = self.get_ground_coordinates(u_b, v_b)
        log.info("ground_coordinates_found", X=X, Y=Y)
        
        # 2. Undistort the top pixel
        pts_t = np.array([[[u_t, v_t]]], dtype=np.float32)
        undistorted_t = cv2.undistortPoints(pts_t, self.mtx, self.dist, P=self.mtx)
        u_t_un, v_t_un = undistorted_t[0][0]
        
        # 3. Solve for Z_height using the projection matrix P
        # s * u_t = P00*X + P01*Y + P02*Z + P03
        # s * v_t = P10*X + P11*Y + P12*Z + P13
        # s       = P20*X + P21*Y + P22*Z + P23
        
        # We substitute 's' into the 'v_t' equation (vertical axis usually has less error for height)
        # (P20*X + P21*Y + P22*Z + P23) * v_t = P10*X + P11*Y + P12*Z + P13
        # Z * (P22 * v_t - P12) = (P10*X + P11*Y + P13) - (P20*X + P21*Y + P23) * v_t
        
        P = self.P
        
        term1 = (P[1,0]*X + P[1,1]*Y + P[1,3])
        term2 = (P[2,0]*X + P[2,1]*Y + P[2,3]) * v_t_un
        
        Z_height = (term1 - term2) / (P[2,2] * v_t_un - P[1,2])
        
        # Also compute using u_t for redundancy / check
        term1_u = (P[0,0]*X + P[0,1]*Y + P[0,3])
        term2_u = (P[2,0]*X + P[2,1]*Y + P[2,3]) * u_t_un
        denom_u = (P[2,2] * u_t_un - P[0,2])
        if abs(denom_u) > 1e-6:
            Z_height_u = (term1_u - term2_u) / denom_u
        else:
            Z_height_u = None
        
        log.debug("height_calculation_debug", Z_from_v=Z_height, Z_from_u=Z_height_u)
        
        # Z is usually positive going away or negative. We take absolute value for physical height.
        # It depends on coordinate system handedness, but height is a magnitude.
        return abs(Z_height)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure height using calibrated matrices.")
    parser.add_argument("--top", type=str, required=True, help="Top pixel coordinate as x,y (e.g. '500,200')")
    parser.add_argument("--bottom", type=str, required=True, help="Bottom pixel coordinate as x,y (e.g. '500,600')")
    
    args = parser.parse_args()
    
    top_tuple = tuple(map(float, args.top.split(",")))
    bottom_tuple = tuple(map(float, args.bottom.split(",")))
    
    try:
        estimator = HeightEstimator()
        height_mm = estimator.calculate_height(top_tuple, bottom_tuple)
        
        print(f"\n--- Measurement Result ---")
        print(f"Top Pixel: {top_tuple}")
        print(f"Bottom Pixel: {bottom_tuple}")
        print(f"Calculated Height: {height_mm:.2f} mm")
        print(f"Calculated Height: {(height_mm / 25.4):.2f} inches")
        
    except Exception as e:
        log.error("measurement_failed", error=str(e))
        print(f"Error: {e}")
