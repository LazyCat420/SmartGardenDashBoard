import numpy as np
import ArducamDepthCamera as ac
import subprocess
import time
import sys

def main():
    print("Capturing RGB picture via rpicam-still...")
    try:
        subprocess.run(['rpicam-still', '-o', 'image.jpg', '--width', '1920', '--height', '1080', '-t', '1000'], check=True)
    except Exception as e:
        print("Warning: RGB capture failed:", e)

    print("Capturing ToF depth map...")
    cam = ac.ArducamCamera()
    if cam.open(ac.Connection.CSI, 8) != 0:
        print("Error: Failed to open ToF camera.")
        sys.exit(1)

    try:
        print("Setting ToF RANGE to 4 meters for better distance...")
        cam.setControl(ac.Control.RANGE, 4)
    except Exception as e:
        print("Warning: Failed to set ToF RANGE:", e)

    if cam.start(ac.FrameType.DEPTH) != 0:
        print("Error: Failed to start ToF camera.")
        cam.close()
        sys.exit(1)

    # Give the ToF sensor 1 second to stabilize lasers
    time.sleep(1)

    frame = cam.requestFrame(2000)
    if frame is not None and isinstance(frame, ac.DepthData):
        depth_buf = frame.depth_data
        np.save('depth.npy', depth_buf)
        print(f"SUCCESS! Saved depth.npy with shape {depth_buf.shape}")
        cam.releaseFrame(frame)
    else:
        print("Error: Failed to capture depth frame.")

    cam.stop()
    cam.close()

if __name__ == '__main__':
    main()
