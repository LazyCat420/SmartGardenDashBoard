import cv2
import numpy as np
import os
import time
import argparse
from pydantic import BaseModel
import structlog
import urllib.request

log = structlog.get_logger()

# Constants
CHECKERBOARD = (9, 6) # Inner corners
CRITERIA = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

class CameraIntrinsics(BaseModel):
    camera_matrix: list[list[float]]
    dist_coeffs: list[list[float]]

class CameraExtrinsics(BaseModel):
    rvec: list[list[float]]
    tvec: list[list[float]]

def load_stream(url: str):
    """Generator to yield frames from an MJPEG stream or fallback to a snapshot endpoint"""
    log.info("connecting_to_stream", url=url)
    try:
        # Check if we can open it as a standard cv2 VideoCapture (works for MJPEG streams)
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                yield frame
        else:
            log.warning("failed_to_open_video_capture", url=url)
    except Exception as e:
        log.error("stream_error", error=str(e))

def calibrate_intrinsics(stream_url: str, square_size_mm: float = 25.0):
    """
    Detects the checkerboard over multiple frames to calculate the intrinsic camera matrix.
    """
    log.info("starting_intrinsic_calibration")
    
    # Prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(8,5,0)
    objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
    objp *= square_size_mm
    
    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane
    
    captured_frames = 0
    required_frames = 15
    last_capture_time = time.time()
    
    gray = None
    
    for frame in load_stream(stream_url):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Find the chess board corners
        ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
        
        # If found, add object points, image points (after refining them)
        if ret == True:
            # Only capture at most once per second to get different angles
            if time.time() - last_capture_time > 1.0:
                objpoints.append(objp)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), CRITERIA)
                imgpoints.append(corners2)
                captured_frames += 1
                last_capture_time = time.time()
                log.info("checkerboard_captured", captured=captured_frames, required=required_frames)
                
            # Draw and display the corners
            cv2.drawChessboardCorners(frame, CHECKERBOARD, corners, ret)
            
        # Draw status text
        cv2.putText(frame, f"Captured: {captured_frames}/{required_frames}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Intrinsic Calibration', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q') or captured_frames >= required_frames:
            break
            
    cv2.destroyAllWindows()
    
    if captured_frames > 0:
        log.info("calculating_intrinsics")
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
        
        intrinsics = CameraIntrinsics(
            camera_matrix=mtx.tolist(),
            dist_coeffs=dist.tolist()
        )
        
        os.makedirs("tools/vision/config", exist_ok=True)
        with open("tools/vision/config/intrinsics.json", "w") as f:
            f.write(intrinsics.model_dump_json(indent=4))
            
        log.info("intrinsics_saved", path="tools/vision/config/intrinsics.json")
        print("✅ Intrinsic calibration complete!")
    else:
        log.warning("no_checkerboards_detected")

def calibrate_extrinsics(stream_url: str, marker_size_mm: float = 50.0):
    """
    Detects an ArUco marker laying flat on the ground to calculate the extrinsic matrix.
    Requires intrinsics.json to be generated first.
    """
    if not os.path.exists("tools/vision/config/intrinsics.json"):
        log.error("missing_intrinsics")
        print("❌ Error: intrinsics.json not found. Run intrinsic calibration first.")
        return
        
    with open("tools/vision/config/intrinsics.json", "r") as f:
        intrinsics = CameraIntrinsics.model_validate_json(f.read())
        
    mtx = np.array(intrinsics.camera_matrix)
    dist = np.array(intrinsics.dist_coeffs)
    
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
    
    # 3D points of the ArUco marker corners in the real world
    # Assuming Z=0 is the soil level, and the marker is centered at (0,0,0)
    half_size = marker_size_mm / 2.0
    obj_points = np.array([
        [-half_size,  half_size, 0],
        [ half_size,  half_size, 0],
        [ half_size, -half_size, 0],
        [-half_size, -half_size, 0]
    ], dtype=np.float32)
    
    for frame in load_stream(stream_url):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, rejectedImgPoints = detector.detectMarkers(gray)
        
        if ids is not None and len(ids) > 0:
            # We only care about marker ID 0
            for i in range(len(ids)):
                if ids[i] == 0:
                    cv2.aruco.drawDetectedMarkers(frame, corners, ids)
                    
                    # Calculate pose
                    ret, rvec, tvec = cv2.solvePnP(obj_points, corners[i][0], mtx, dist)
                    
                    if ret:
                        cv2.drawFrameAxes(frame, mtx, dist, rvec, tvec, marker_size_mm)
                        
                        extrinsics = CameraExtrinsics(
                            rvec=rvec.tolist(),
                            tvec=tvec.tolist()
                        )
                        
                        with open("tools/vision/config/extrinsics.json", "w") as f:
                            f.write(extrinsics.model_dump_json(indent=4))
                            
                        log.info("extrinsics_saved", path="tools/vision/config/extrinsics.json")
                        print("✅ Extrinsic calibration complete! Ground plane (Z=0) locked.")
                        
                        # Show result for a few seconds
                        cv2.imshow('Extrinsic Calibration', frame)
                        cv2.waitKey(3000)
                        cv2.destroyAllWindows()
                        return
        
        cv2.putText(frame, "Looking for ArUco Marker ID 0 flat on soil...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow('Extrinsic Calibration', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate camera for monocular height estimation.")
    parser.add_argument("--mode", choices=["intrinsics", "extrinsics"], required=True)
    parser.add_argument("--stream", type=str, default="http://localhost:5001/stream", help="URL of the MJPEG stream")
    parser.add_argument("--size", type=float, default=25.0, help="Size of the checkerboard square or ArUco marker in mm")
    
    args = parser.parse_args()
    
    if args.mode == "intrinsics":
        calibrate_intrinsics(args.stream, args.size)
    elif args.mode == "extrinsics":
        calibrate_extrinsics(args.stream, args.size)
