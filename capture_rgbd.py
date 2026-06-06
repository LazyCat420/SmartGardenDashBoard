import numpy as np
import ArducamDepthCamera as ac
import subprocess
import time
import sys

# ── Configuration ────────────────────────────────────────────────
# Near Mode = 2  (0.2m – 2m, 37.5 MHz modulation — precise at close range)
# Far Mode  = 4  (up to 4m, 75 MHz modulation — saturates at close range)
# For objects < 2 feet away, Near Mode is REQUIRED or the sensor saturates.
MAX_DISTANCE = 2

# Minimum confidence threshold (0-255).
# Pixels below this are unreliable (saturation, multipath, noise).
# ArduCam's own examples use 30 as default.
CONFIDENCE_THRESHOLD = 30

# Number of frames to average for noise reduction at close range.
# More frames = smoother depth but slower capture.
FRAME_AVG_COUNT = 5

# Warm-up frames to discard (sensor needs time to auto-expose).
WARMUP_FRAMES = 8


def main():
    print("Capturing RGB picture via rpicam-still...")
    try:
        subprocess.run(
            ['rpicam-still', '-o', 'image.jpg',
             '--width', '1920', '--height', '1080', '-t', '1000'],
            check=True
        )
    except Exception as e:
        print("Warning: RGB capture failed:", e)

    print("Capturing ToF depth map...")
    cam = ac.ArducamCamera()
    if cam.open(ac.Connection.CSI, 8) != 0:
        print("Error: Failed to open ToF camera.")
        sys.exit(1)

    # Start with DEPTH frame type first
    # (setControl must be called AFTER start on some firmware versions)
    if cam.start(ac.FrameType.DEPTH) != 0:
        print("Error: Failed to start ToF camera.")
        cam.close()
        sys.exit(1)

    # Now set range AFTER start — some firmware ignores pre-start controls
    try:
        print(f"Setting ToF RANGE to {MAX_DISTANCE} (Near Mode)...")
        cam.setControl(ac.Control.RANGE, MAX_DISTANCE)
    except Exception as e:
        print("Warning: Failed to set ToF RANGE:", e)

    # ── Warm-up: discard initial frames while sensor auto-adjusts ──
    print(f"Warming up sensor ({WARMUP_FRAMES} frames)...")
    for i in range(WARMUP_FRAMES):
        f = cam.requestFrame(2000)
        if f is not None:
            cam.releaseFrame(f)
        time.sleep(0.05)

    # ── Capture: average multiple frames for noise reduction ──────
    print(f"Capturing {FRAME_AVG_COUNT} frames for averaging...")
    depth_stack = []
    for i in range(FRAME_AVG_COUNT):
        frame = cam.requestFrame(2000)
        if frame is not None and isinstance(frame, ac.DepthData):
            depth_buf = frame.depth_data.copy()
            depth_stack.append(depth_buf)
            cam.releaseFrame(frame)
        else:
            print(f"  Warning: Frame {i+1} capture failed, skipping.")
        time.sleep(0.05)

    cam.stop()
    cam.close()

    if not depth_stack:
        print("Error: Failed to capture any depth frames.")
        sys.exit(1)

    # ── Post-processing ──────────────────────────────────────────
    # Stack all frames and compute the median (robust to outliers)
    all_frames = np.stack(depth_stack, axis=0)
    depth_median = np.median(all_frames, axis=0).astype(np.float32)

    # Convert to millimeters (ArduCam outputs meters as float32)
    # Check if values seem to be in meters (all < 10) vs already in mm
    if depth_median.max() < 20:
        # Values are in meters, convert to mm
        depth_mm = depth_median * 1000.0
    else:
        # Already in mm
        depth_mm = depth_median

    # Zero out unreliable pixels:
    # - Negative values (sensor error)
    # - Zero values (no return / saturated)
    # - Values beyond MAX_DISTANCE * 1000 mm + margin
    max_valid_mm = MAX_DISTANCE * 1000 + 500  # 2500mm for near mode
    depth_mm[depth_mm <= 0] = 0
    depth_mm[depth_mm > max_valid_mm] = 0

    # Report statistics
    valid = depth_mm[depth_mm > 0]
    if valid.size > 0:
        print(f"SUCCESS! Depth stats: min={valid.min():.0f}mm, "
              f"max={valid.max():.0f}mm, mean={valid.mean():.0f}mm, "
              f"valid_pixels={valid.size}/{depth_mm.size} "
              f"({100*valid.size/depth_mm.size:.1f}%)")
    else:
        print("WARNING: All depth values are zero/invalid! "
              "Check camera placement and lighting.")

    np.save('depth.npy', depth_mm)
    print(f"Saved depth.npy with shape {depth_mm.shape}")


if __name__ == '__main__':
    main()
