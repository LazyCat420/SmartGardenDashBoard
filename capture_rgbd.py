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

# Minimum confidence/amplitude threshold (0-255).
# Pixels below this are unreliable (saturation, multipath, noise).
# ArduCam's own examples use 30 as default.
CONFIDENCE_THRESHOLD = 30

# Number of frames to average for noise reduction at close range.
# More frames = smoother depth but slower capture.
FRAME_AVG_COUNT = 5

# Warm-up frames to discard (sensor needs time to auto-expose).
# Increased from 8 to 12 for near-mode stabilization.
WARMUP_FRAMES = 12

# CSI indices to try (varies by Pi model and camera port)
CSI_INDICES = [8, 0, 2, 4]


def _get_depth_and_confidence(frame):
    """Extract depth and confidence arrays from a frame object.

    Handles both old and new ArducamDepthCamera SDK API:
      - New API: frame.getDepthData(), frame.getConfidenceData()
      - Legacy:  frame.depth_data (no confidence available)

    Returns (depth_array, confidence_array_or_None).
    """
    depth_buf = None
    conf_buf = None

    # ── Try new-style method API first ──────────────────────────
    if hasattr(frame, 'getDepthData') and callable(frame.getDepthData):
        try:
            depth_buf = np.asanyarray(frame.getDepthData()).copy()
        except Exception:
            depth_buf = None

    if hasattr(frame, 'getConfidenceData') and callable(frame.getConfidenceData):
        try:
            conf_buf = np.asanyarray(frame.getConfidenceData()).copy()
        except Exception:
            conf_buf = None

    # If getConfidenceData doesn't exist, try getAmplitudeData (same purpose)
    if conf_buf is None and hasattr(frame, 'getAmplitudeData') and callable(frame.getAmplitudeData):
        try:
            conf_buf = np.asanyarray(frame.getAmplitudeData()).copy()
        except Exception:
            conf_buf = None

    # ── Fall back to legacy attribute API ───────────────────────
    if depth_buf is None:
        if hasattr(frame, 'depth_data') and frame.depth_data is not None:
            try:
                depth_buf = np.asanyarray(frame.depth_data).copy()
            except Exception:
                depth_buf = None

    if conf_buf is None:
        if hasattr(frame, 'confidence_data') and frame.confidence_data is not None:
            try:
                conf_buf = np.asanyarray(frame.confidence_data).copy()
            except Exception:
                conf_buf = None

    return depth_buf, conf_buf


def _open_camera(cam):
    """Try opening the ToF camera on multiple CSI indices.

    Returns the index that succeeded, or -1 on failure.
    """
    for idx in CSI_INDICES:
        try:
            ret = cam.open(ac.Connection.CSI, idx)
            if ret == 0:
                print(f"ToF camera opened on CSI index {idx}")
                return idx
        except Exception as e:
            print(f"  CSI index {idx} failed: {e}")
    return -1


def main():
    import os
    # Delete stale files to prevent copying back old data on failure
    for f in ['image.jpg', 'depth.npy', 'confidence.npy']:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception as e:
            print(f"Warning: Failed to delete stale file {f}: {e}")

    print("Capturing RGB picture via rpicam-still...")
    try:
        subprocess.run(
            ['rpicam-still', '-o', 'image.jpg',
             '--width', '1920', '--height', '1080', '-t', '1000'],
            check=True,
            timeout=15
        )
    except Exception as e:
        print("Error: RGB capture failed:", e, file=sys.stderr)
        sys.exit(1)

    print("Capturing ToF depth map...")

    # Print SDK version if available
    if hasattr(ac, '__version__'):
        print(f"  ArducamDepthCamera SDK version: {ac.__version__}")

    cam = ac.ArducamCamera()

    # Auto-detect CSI index instead of hardcoding
    idx = _open_camera(cam)
    if idx < 0:
        print("Error: Failed to open ToF camera on any CSI index.")
        print(f"  Tried indices: {CSI_INDICES}")
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
    conf_stack = []
    has_confidence = False

    for i in range(FRAME_AVG_COUNT):
        frame = cam.requestFrame(2000)
        if frame is not None:
            depth_buf, conf_buf = _get_depth_and_confidence(frame)

            if depth_buf is not None:
                depth_stack.append(depth_buf)

                if conf_buf is not None:
                    conf_stack.append(conf_buf)
                    has_confidence = True
                    # Per-frame diagnostics
                    valid_conf = np.sum(conf_buf >= CONFIDENCE_THRESHOLD)
                    total_px = conf_buf.size
                    print(f"  Frame {i+1}: {valid_conf}/{total_px} pixels above "
                          f"confidence threshold ({100*valid_conf/total_px:.1f}%)")
                else:
                    print(f"  Frame {i+1}: captured depth (no confidence data available)")
            else:
                print(f"  Warning: Frame {i+1} returned no depth data, skipping.")

            cam.releaseFrame(frame)
        else:
            print(f"  Warning: Frame {i+1} capture failed (requestFrame returned None), skipping.")
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

    # ── Confidence filtering ─────────────────────────────────────
    # Zero out pixels where the sensor has low confidence/amplitude.
    # This is the KEY fix — without this, saturated/noisy pixels
    # create an all-zero depth map that renders as solid red.
    if has_confidence and conf_stack:
        all_conf = np.stack(conf_stack, axis=0)
        conf_median = np.median(all_conf, axis=0).astype(np.float32)

        # Zero out low-confidence pixels
        low_conf_mask = conf_median < CONFIDENCE_THRESHOLD
        depth_median[low_conf_mask] = 0

        low_conf_count = np.sum(low_conf_mask)
        total_px = low_conf_mask.size
        print(f"Confidence filter: zeroed {low_conf_count}/{total_px} "
              f"low-confidence pixels ({100*low_conf_count/total_px:.1f}%)")

        # Save confidence map for backend diagnostics
        np.save('confidence.npy', conf_median)
        print(f"Saved confidence.npy with shape {conf_median.shape}")
    else:
        print("Warning: No confidence data available — depth map is unfiltered.")
        print("  This may cause noisy/saturated pixels to appear as invalid.")

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
        print("  Possible causes:")
        print("  - Object too close (< 10cm) causing sensor saturation")
        print("  - Object too far (> 2m in Near Mode)")
        print("  - Protective film still on sensor aperture")
        print("  - Highly reflective or very dark surface")

    np.save('depth.npy', depth_mm)
    print(f"Saved depth.npy with shape {depth_mm.shape}")


if __name__ == '__main__':
    main()
