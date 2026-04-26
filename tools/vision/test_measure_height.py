import os
import json
import pytest
import numpy as np
import cv2
from measure_height import HeightEstimator

def test_height_estimator(tmp_path):
    """
    Simulates a perfect pinhole camera pointing down at a 45 degree angle.
    Verifies that a known 3D point (e.g. height 100mm) projects to a 2D pixel,
    and then the estimator correctly recalculates the 100mm height from the pixels.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    
    # 1. Create fake intrinsic matrix (Focal length 1000, Center 640x360)
    fx, fy = 1000.0, 1000.0
    cx, cy = 640.0, 360.0
    mtx = [
        [fx, 0.0, cx],
        [0.0, fy, cy],
        [0.0, 0.0, 1.0]
    ]
    dist = [[0.0, 0.0, 0.0, 0.0, 0.0]]
    
    with open(config_dir / "intrinsics.json", "w") as f:
        json.dump({"camera_matrix": mtx, "dist_coeffs": dist}, f)
        
    # 2. Create fake extrinsic matrix
    # Camera is located at (0, -500, 500) pointing towards origin (0,0,0)
    # Pitch down by 45 degrees
    theta = np.radians(-45)
    R_x = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(theta), -np.sin(theta)],
        [0.0, np.sin(theta), np.cos(theta)]
    ])
    
    # solvePnP outputs rvec. Let's create an rvec from this rotation
    rvec, _ = cv2.Rodrigues(R_x)
    
    # Translation vector: T = -R * C
    C = np.array([[0.0], [-500.0], [500.0]])
    tvec = -np.dot(R_x, C)
    
    with open(config_dir / "extrinsics.json", "w") as f:
        json.dump({"rvec": rvec.tolist(), "tvec": tvec.tolist()}, f)
        
    # Initialize estimator
    estimator = HeightEstimator(config_dir=str(config_dir))
    
    # 3. Simulate a real plant
    # Plant is at X=0, Y=100. Height is 250mm
    plant_base_3d = np.array([[0.0], [100.0], [0.0]], dtype=np.float32)
    plant_top_3d = np.array([[0.0], [100.0], [250.0]], dtype=np.float32)
    
    # Project them to pixels using standard OpenCV
    mtx_np = np.array(mtx, dtype=np.float32)
    dist_np = np.array(dist, dtype=np.float32)
    rvec_np = np.array(rvec, dtype=np.float32)
    tvec_np = np.array(tvec, dtype=np.float32)
    
    base_pixel, _ = cv2.projectPoints(plant_base_3d, rvec_np, tvec_np, mtx_np, dist_np)
    top_pixel, _ = cv2.projectPoints(plant_top_3d, rvec_np, tvec_np, mtx_np, dist_np)
    
    u_b, v_b = base_pixel[0][0]
    u_t, v_t = top_pixel[0][0]
    
    # 4. Feed the simulated pixels back into our math engine
    calculated_height = estimator.calculate_height(top_pixel=(u_t, v_t), bottom_pixel=(u_b, v_b))
    
    # The calculated height should be perfectly 250.0mm
    assert np.isclose(calculated_height, 250.0, atol=0.1), f"Expected 250.0, got {calculated_height}"
    
    # Check ground coordinate calculation
    X, Y = estimator.get_ground_coordinates(u_b, v_b)
    assert np.isclose(X, 0.0, atol=0.1)
    assert np.isclose(Y, 100.0, atol=0.1)
    
    print("Pytest: 3D Ray-casting math is verified and pixel-perfect.")
