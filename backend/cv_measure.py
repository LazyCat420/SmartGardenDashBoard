"""
CV Measure — YOLO + OpenCV based object detection and measurement.

Uses YOLOv8-nano for reference object detection (COCO classes) and
OpenCV contour analysis for plant segmentation.  Converts pixel
measurements to real-world centimeters via a known reference object.
"""

import os
import io
import logging
from pathlib import Path

# NOTE: cv2 and numpy are imported lazily inside functions to avoid
# crashing the entire app if OpenCV system libs are missing.
# This way the dashboard still serves other endpoints.

logger = logging.getLogger(__name__)

# ── YOLO model singleton ─────────────────────────────────────────
_yolo_model = None

# ── Depth model singleton ────────────────────────────────────────
_depth_model = None
_depth_transform = None

# Directory where captured images are stored (same as camera_service)
CAPTURES_DIR = os.environ.get('CAPTURES_DIR', '/app/captures')

# Depth grid resolution (sent to frontend for client-side lookups)
DEPTH_GRID_SIZE = 64

# COCO class IDs useful for reference objects
# 39 = bottle, 67 = cell phone, 73 = book, 76 = scissors
COCO_REFERENCE_MAP = {
    'soda_can': [39],       # 'bottle' class covers cans too
    'bottle': [39],
    'cell_phone': [67],
    'book': [73],
    'scissors': [76],
}

# Known dimensions (height_cm, width_cm) for reference objects
# height = longer dimension, width = shorter dimension
KNOWN_DIMENSIONS = {
    'soda_can':    {'height_cm': 12.2,  'width_cm': 6.6},
    'aa_battery':  {'height_cm': 5.05,  'width_cm': 1.45},
    'bic_lighter': {'height_cm': 8.0,   'width_cm': 2.5},
    'credit_card': {'height_cm': 8.56,  'width_cm': 5.4},
}


def _get_yolo_model():
    """Lazy-load the YOLOv8-nano model (singleton)."""
    global _yolo_model
    if _yolo_model is not None:
        return _yolo_model

    try:
        from ultralytics import YOLO

        # Check for a pre-bundled ONNX model first, fall back to PT
        model_dir = Path(__file__).parent / 'models'
        onnx_path = model_dir / 'yolov8n.onnx'
        pt_path = model_dir / 'yolov8n.pt'

        if onnx_path.is_file():
            _yolo_model = YOLO(str(onnx_path), task='detect')
            logger.info("Loaded YOLOv8-nano ONNX model from %s", onnx_path)
        elif pt_path.is_file():
            _yolo_model = YOLO(str(pt_path))
            logger.info("Loaded YOLOv8-nano PT model from %s", pt_path)
        else:
            # Download default nano model (will be cached)
            _yolo_model = YOLO('yolov8n.pt')
            logger.info("Downloaded YOLOv8-nano model (first run)")

        return _yolo_model
    except ImportError:
        logger.warning("ultralytics not installed — YOLO detection unavailable")
        return None
    except Exception as exc:
        logger.error("Failed to load YOLO model: %s", exc)
        return None


# ── ToF Depth Loader ─────────────────────────────────────────────

def load_tof_depth_grid(depth_path, target_shape=(1080, 1920), rotation=0, hflip=False, vflip=False):
    """
    Load physical ToF depth map in millimeters.
    
    Reads the depth.npy array, optionally applies confidence filtering
    from the companion confidence.npy file, scales to match the RGB
    image size, and returns it as a numpy array in millimeters.
    
    Returns:
        numpy.ndarray of depth in millimeters, sized to target_shape
        or None if loading fails.
    """
    import numpy as np
    import cv2
    
    if not depth_path or not os.path.exists(depth_path):
        return None
        
    try:
        depth_buf = np.load(depth_path)
        
        # ── Load and apply confidence filter if available ────────
        # The updated capture_rgbd.py saves confidence.npy alongside
        # depth.npy.  Apply it here to zero out unreliable pixels.
        conf_path = depth_path.replace('_depth.npy', '_confidence.npy')
        if not os.path.exists(conf_path):
            # Also check for non-suffixed companion (Pi-side naming)
            conf_path_alt = os.path.join(
                os.path.dirname(depth_path), 'confidence.npy'
            )
            if os.path.exists(conf_path_alt):
                conf_path = conf_path_alt
            else:
                conf_path = None

        if conf_path and os.path.exists(conf_path):
            try:
                conf_buf = np.load(conf_path)
                if conf_buf.shape == depth_buf.shape:
                    low_conf = conf_buf < 30  # Same threshold as capture
                    zeroed = int(np.sum(low_conf))
                    if zeroed > 0:
                        depth_buf[low_conf] = 0
                        logger.info("Confidence filter applied: zeroed %d/%d "
                                    "low-confidence pixels (%.1f%%)",
                                    zeroed, depth_buf.size,
                                    100 * zeroed / depth_buf.size)
                else:
                    logger.warning("Confidence shape %s doesn't match depth "
                                   "shape %s — skipping filter",
                                   conf_buf.shape, depth_buf.shape)
            except Exception as conf_exc:
                logger.warning("Failed to load confidence map: %s", conf_exc)

        # Diagnostic logging — helps verify ToF Near Mode is working
        valid = depth_buf[depth_buf > 0]
        if valid.size > 0:
            logger.info("ToF depth loaded: shape=%s, min=%.0fmm, max=%.0fmm, "
                        "mean=%.0fmm, valid=%d/%d (%.1f%%)",
                        depth_buf.shape, valid.min(), valid.max(), valid.mean(),
                        valid.size, depth_buf.size,
                        100 * valid.size / depth_buf.size)
        else:
            logger.warning("ToF depth loaded but ALL values are zero/invalid! "
                          "shape=%s — sensor may be saturated or misconfigured",
                          depth_buf.shape)
            return None
        
        # Apply same flips/rotations as RGB camera
        if hflip:
            depth_buf = cv2.flip(depth_buf, 1)
        if vflip:
            depth_buf = cv2.flip(depth_buf, 0)

        if rotation == 90:
            depth_buf = cv2.rotate(depth_buf, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            depth_buf = cv2.rotate(depth_buf, cv2.ROTATE_180)
        elif rotation == 270:
            depth_buf = cv2.rotate(depth_buf, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # ToF array is usually 240x180. Resize to match RGB (1920x1080)
        # INTER_NEAREST to avoid interpolating invalid edge depths,
        # but INTER_LINEAR gives smoother depth maps for bounding boxes.
        depth_resized = cv2.resize(depth_buf, (target_shape[1], target_shape[0]), 
                                   interpolation=cv2.INTER_LINEAR)
        return depth_resized
    except Exception as exc:
        logger.error("Failed to load ToF depth map: %s", exc)
        return None


def calculate_physical_size(px_width, px_height, distance_mm, img_width=1920, img_height=1080):
    """
    Calculate physical size using pinhole camera trigonometry and laser distance.
    Assumes Raspberry Pi Camera Module 3 Wide (IMX708).
    HFOV = 102 degrees, VFOV = 67 degrees.
    """
    import math
    
    if distance_mm <= 0:
        return None, None
        
    # FOV in radians
    hfov_rad = math.radians(102.0)
    vfov_rad = math.radians(67.0)
    
    # Distance in cm
    dist_cm = distance_mm / 10.0
    
    # Physical width and height of the entire frame at this distance
    frame_width_cm = 2.0 * dist_cm * math.tan(hfov_rad / 2.0)
    frame_height_cm = 2.0 * dist_cm * math.tan(vfov_rad / 2.0)
    
    # Proportion of the object in the frame
    obj_width_cm = frame_width_cm * (px_width / float(img_width))
    obj_height_cm = frame_height_cm * (px_height / float(img_height))
    
    return round(obj_width_cm, 1), round(obj_height_cm, 1)

def generate_tof_depth_grid(tof_depth, grid_size=64):
    """Downsample and normalize ToF depth to 0-1 for the UI heatmap."""
    import cv2
    import numpy as np
    
    if tof_depth is None:
        return None
        
    depth_small = cv2.resize(tof_depth, (grid_size, grid_size), interpolation=cv2.INTER_AREA)
    
    # Ignore 0 values (invalid) and extreme outliers (>6000mm)
    valid_mask = (depth_small > 0) & (depth_small < 6000)
    if not np.any(valid_mask):
        return [[0.5] * grid_size for _ in range(grid_size)]
        
    d_min = depth_small[valid_mask].min()
    d_max = depth_small[valid_mask].max()
    
    # Normalize to 0-1 (closer = 0, farther = 1)
    if d_max > d_min:
        depth_norm = (depth_small - d_min) / (d_max - d_min)
    else:
        depth_norm = np.zeros_like(depth_small)
        
    # Cap invalid pixels to max distance
    depth_norm[~valid_mask] = 1.0
    
    return [[round(float(v), 3) for v in row] for row in depth_norm]

def _apply_transforms(image, rotation=0, hflip=False, vflip=False):
    """Apply rotation and flip transforms to a cv2 image (BGR)."""
    import cv2
    if hflip:
        image = cv2.flip(image, 1)
    if vflip:
        image = cv2.flip(image, 0)

    if rotation == 90:
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        image = cv2.rotate(image, cv2.ROTATE_180)
    elif rotation == 270:
        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    return image


def _load_image(image_path, rotation=0, hflip=False, vflip=False):
    """Load an image from disk with safety checks and transforms."""
    import cv2
    resolved = os.path.realpath(image_path)
    captures_real = os.path.realpath(CAPTURES_DIR) + os.sep

    if not resolved.startswith(captures_real):
        raise ValueError("Image path outside captures directory")

    img = cv2.imread(resolved)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    img = _apply_transforms(img, rotation, hflip, vflip)
    return img


# ── YOLO-based reference object detection ────────────────────────

def detect_reference_yolo(image, ref_type):
    """
    Detect a reference object using YOLOv8-nano.

    Returns the best bounding box as (x, y, w, h) in pixels,
    or None if no matching object was found.
    """
    model = _get_yolo_model()
    if model is None:
        return None

    target_classes = COCO_REFERENCE_MAP.get(ref_type)
    if not target_classes:
        return None  # This ref_type isn't a COCO class

    results = model(image, verbose=False, conf=0.3)

    best_box = None
    best_conf = 0.0

    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])

            if cls_id in target_classes and conf > best_conf:
                # xyxy format → (x, y, w, h)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                best_box = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                best_conf = conf

    if best_box:
        logger.info("YOLO detected %s with confidence %.2f at %s",
                     ref_type, best_conf, best_box)

    return best_box


# ── OpenCV contour-based reference object detection ──────────────

# Expected size of each reference object relative to image area.
# Format: (min_fraction, ideal_fraction, max_fraction) of image area.
# A 1920x1080 image = ~2M pixels.  AA battery ≈ 50×140px = 7000px² ≈ 0.003
EXPECTED_SIZE_FRACTIONS = {
    'aa_battery':  (0.0005, 0.004,  0.03),   # Very small object
    'bic_lighter': (0.001,  0.008,  0.05),    # Small object
    'credit_card': (0.005,  0.02,   0.10),    # Medium object
    'soda_can':    (0.005,  0.03,   0.12),    # Medium-large object
}


def detect_reference_contour(image, ref_type):
    """
    Detect a reference object using OpenCV contour analysis.

    Uses edge detection + aspect ratio filtering + expected-size scoring
    based on the known dimensions of the reference object type.

    Returns the best bounding box as (x, y, w, h) in pixels,
    or None if no suitable contour was found.
    """
    dims = KNOWN_DIMENSIONS.get(ref_type)
    if not dims:
        return None

    import cv2
    import math

    expected_aspect = dims['height_cm'] / dims['width_cm']
    # Allow ±40% tolerance on aspect ratio
    min_aspect = expected_aspect * 0.6
    max_aspect = expected_aspect * 1.4

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h_img, w_img = gray.shape[:2]
    img_area = h_img * w_img

    # Get expected size range for this object type
    size_fracs = EXPECTED_SIZE_FRACTIONS.get(ref_type, (0.001, 0.01, 0.15))
    min_area = img_area * size_fracs[0]
    ideal_area = img_area * size_fracs[1]
    max_area = img_area * size_fracs[2]

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive thresholding for better edge detection in varied lighting
    edges = cv2.Canny(blurred, 50, 150)

    # Dilate to close gaps in edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=2)

    # Close small gaps
    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_close, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)

    candidates = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        # Get the minimum bounding rectangle
        rect = cv2.minAreaRect(contour)
        box_w, box_h = rect[1]

        if box_w < 5 or box_h < 5:
            continue

        # Ensure height > width for aspect ratio comparison
        if box_w > box_h:
            box_w, box_h = box_h, box_w

        aspect = box_h / box_w

        if min_aspect <= aspect <= max_aspect:
            # Get the upright bounding rect
            x, y, w, h = cv2.boundingRect(contour)

            # ── Score based on aspect match + size match ─────────
            # Aspect score: 1.0 = perfect match, 0.0 = at tolerance edge
            aspect_diff = abs(aspect - expected_aspect) / expected_aspect
            aspect_score = max(0.0, 1.0 - aspect_diff)

            # Size score: Gaussian penalty — peaks at ideal_area, drops off
            # for objects that are way too big or too small
            if ideal_area > 0:
                log_ratio = math.log(area / ideal_area)
                size_score = math.exp(-0.5 * (log_ratio / 1.0) ** 2)
            else:
                size_score = 1.0

            # Combined score: aspect match matters most, size is a filter
            score = aspect_score * size_score

            candidates.append((score, (x, y, w, h), area, aspect))
            logger.debug("Contour candidate: bbox=(%d,%d,%d,%d) area=%d "
                         "aspect=%.2f aspect_score=%.3f size_score=%.3f "
                         "total=%.3f",
                         x, y, w, h, area, aspect,
                         aspect_score, size_score, score)

    if not candidates:
        logger.info("No contours matched %s (checked %d contours, "
                     "area range %.0f-%.0f, aspect range %.2f-%.2f)",
                     ref_type, len(contours), min_area, max_area,
                     min_aspect, max_aspect)
        return None

    # Return the best candidate
    candidates.sort(key=lambda c: c[0], reverse=True)
    best = candidates[0]
    logger.info("OpenCV contour detected %s at %s (score=%.3f area=%d "
                 "aspect=%.2f, from %d candidates)",
                 ref_type, best[1], best[0], best[2], best[3],
                 len(candidates))
    return best[1]



# ── Plant detection via HSV green segmentation ───────────────────

def detect_plant_contour(image, exclude_bbox=None):
    """
    Detect the plant in the image using HSV green-color segmentation.

    Parameters:
        image: cv2 BGR image
        exclude_bbox: Optional (x, y, w, h) of the reference object to
                      mask out before plant detection.

    Returns the bounding box as (x, y, w, h) in pixels,
    or None if no plant-like region was found.
    """
    import cv2
    import numpy as np

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h_img, w_img = image.shape[:2]

    # Green color ranges (covers light green to dark green)
    lower_green1 = np.array([25, 30, 30])
    upper_green1 = np.array([90, 255, 255])

    mask = cv2.inRange(hsv, lower_green1, upper_green1)

    # Also capture some yellow-green (new growth)
    lower_yellow_green = np.array([20, 40, 40])
    upper_yellow_green = np.array([35, 255, 255])
    mask2 = cv2.inRange(hsv, lower_yellow_green, upper_yellow_green)
    mask = cv2.bitwise_or(mask, mask2)

    # Mask out the reference object area if provided
    if exclude_bbox:
        ex, ey, ew, eh = exclude_bbox
        # Expand exclusion zone by 10% for safety
        pad_x = int(ew * 0.1)
        pad_y = int(eh * 0.1)
        x1 = max(0, ex - pad_x)
        y1 = max(0, ey - pad_y)
        x2 = min(w_img, ex + ew + pad_x)
        y2 = min(h_img, ey + eh + pad_y)
        mask[y1:y2, x1:x2] = 0

    # Morphological operations to clean up the mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        logger.info("No plant-like green regions detected")
        return None

    # Find the largest green contour (likely the plant)
    min_area = h_img * w_img * 0.005  # At least 0.5% of image
    valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]

    if not valid_contours:
        # If no single contour is big enough, try combining nearby ones
        all_points = np.vstack(contours)
        x, y, w, h = cv2.boundingRect(all_points)
        combined_area = w * h
        if combined_area > min_area:
            logger.info("Plant detected via combined contours at (%d,%d,%d,%d)",
                         x, y, w, h)
            return (x, y, w, h)
        return None

    # Use the bounding rect of the largest contour
    largest = max(valid_contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    logger.info("Plant detected at (%d,%d,%d,%d) — area=%d px²",
                 x, y, w, h, cv2.contourArea(largest))
    return (x, y, w, h)

# ── VLM-based Battery Detection (Jetson Orin AGX) ────────────────

# Jetson Orin AGX endpoint running vLLM with vision model
VLM_ENDPOINT = os.environ.get(
    'VLM_ENDPOINT', 'http://10.0.0.30:8000/v1/chat/completions'
)
VLM_MODEL = os.environ.get(
    'VLM_MODEL', 'Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16'
)
VLM_TIMEOUT = int(os.environ.get('VLM_TIMEOUT', '30'))


def vlm_detect_battery(image):
    """Detect an AA battery using a Vision Language Model.

    Sends the image to the Jetson Orin AGX running a Qwen3.5 vision model
    via vLLM's OpenAI-compatible API.  The VLM *understands* what a battery
    looks like — it doesn't rely on fragile color/shape heuristics.

    Returns the bounding box as (x, y, w, h) in pixels and a confidence
    score, or (None, 0.0) if detection fails or the VLM is unavailable.
    """
    import json
    import base64

    try:
        import requests as http_requests
    except ImportError:
        logger.warning("requests library not available for VLM detection")
        return None, 0.0

    try:
        import cv2
        import numpy as np
    except ImportError:
        logger.warning("cv2/numpy not available for VLM detection")
        return None, 0.0

    h_img, w_img = image.shape[:2]

    # Encode the image as base64 JPEG
    try:
        _, buf = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
    except Exception as exc:
        logger.error("VLM detect: failed to encode image: %s", exc)
        return None, 0.0

    prompt = (
        "Look at this image carefully. Is there an AA battery visible? "
        "If yes, return ONLY a JSON object with the battery's bounding box "
        "in pixel coordinates:\n"
        '{"found": true, "x": <left>, "y": <top>, "width": <w>, "height": <h>, '
        '"confidence": <0.0 to 1.0>}\n\n'
        f"The image is {w_img}x{h_img} pixels. "
        "x and y are the top-left corner of the bounding box. "
        "width and height are the box dimensions in pixels. "
        "Be precise — the box should tightly wrap the battery.\n\n"
        'If no AA battery is visible, return: {"found": false}\n\n'
        "Return ONLY the JSON, no markdown, no explanation."
    )

    payload = {
        "model": VLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 256,
        "temperature": 0.1,
    }

    try:
        logger.info("VLM battery detection: sending to %s (model=%s, "
                     "image=%dx%d)", VLM_ENDPOINT, VLM_MODEL, w_img, h_img)

        resp = http_requests.post(
            VLM_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=VLM_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract content from OpenAI-compatible response
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        # Strip markdown fences if present
        clean = content.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines).strip()

        # Handle <think> blocks from Qwen3.5 thinking mode
        if "<think>" in clean:
            # Remove everything between <think> and </think>
            import re
            clean = re.sub(r'<think>.*?</think>', '', clean,
                           flags=re.DOTALL).strip()

        result = json.loads(clean)

        if not result.get("found"):
            logger.info("VLM says no battery found in image")
            return None, 0.0

        x = int(result.get("x", 0))
        y = int(result.get("y", 0))
        w = int(result.get("width", 0))
        h = int(result.get("height", 0))
        conf = float(result.get("confidence", 0.8))

        # Sanity checks
        if w < 5 or h < 5:
            logger.warning("VLM returned tiny bbox (%d,%d,%d,%d), ignoring",
                           x, y, w, h)
            return None, 0.0

        # Clamp to image bounds
        x = max(0, min(x, w_img - 1))
        y = max(0, min(y, h_img - 1))
        w = min(w, w_img - x)
        h = min(h, h_img - y)

        logger.info("VLM detected battery at (%d,%d,%d,%d) conf=%.2f",
                     x, y, w, h, conf)
        return (x, y, w, h), conf

    except http_requests.exceptions.ConnectionError:
        logger.warning("VLM endpoint unreachable at %s — falling back to "
                       "OpenCV", VLM_ENDPOINT)
        return None, 0.0
    except http_requests.exceptions.Timeout:
        logger.warning("VLM request timed out after %ds — falling back to "
                       "OpenCV", VLM_TIMEOUT)
        return None, 0.0
    except json.JSONDecodeError as exc:
        logger.warning("VLM returned non-JSON response: %s (raw: %s)",
                       exc, content[:300] if 'content' in dir() else '?')
        return None, 0.0
    except Exception as exc:
        logger.warning("VLM detection failed: %s — falling back to OpenCV",
                       exc)
        return None, 0.0


# ── Automatic AA Battery Detection ───────────────────────────────

def auto_detect_battery(image):
    """Detect an AA battery in the image using color + shape analysis.

    Multi-stage pipeline:
      1. Color filter — isolate metallic silver/copper/gold tones,
         exclude greens (plants) and browns (soil)
      2. Edge detection on filtered regions
      3. Contour analysis with aspect ratio (~3.48:1), size, and
         rectangularity scoring
      4. Fallback: pure shape-based detection (no color filter) if
         color-based search finds nothing — handles dark-body batteries

    Returns the best bounding box as (x, y, w, h) in pixels and a
    confidence score, or (None, 0.0) if no battery was found.
    """
    try:
        import cv2
        import numpy as np
        import math
    except ImportError as exc:
        logger.error("auto_detect_battery: missing dependency: %s", exc)
        return None, 0.0

    try:
        h_img, w_img = image.shape[:2]
        img_area = h_img * w_img

        # Expected aspect ratio: 5.05 / 1.45 ≈ 3.48
        EXPECTED_ASPECT = 5.05 / 1.45
        ASPECT_TOL = 0.40  # ±40% tolerance (widened from 35%)
        min_aspect = EXPECTED_ASPECT * (1 - ASPECT_TOL)
        max_aspect = EXPECTED_ASPECT * (1 + ASPECT_TOL)

        # Expected size range (fraction of image area)
        # A battery in a 1920×1080 frame is roughly 40-150px wide × 140-500px tall
        MIN_AREA_FRAC = 0.0002   # ~400 px² in 2M image (lowered)
        MAX_AREA_FRAC = 0.05     # ~100000 px² (raised)
        IDEAL_AREA_FRAC = 0.005  # ~10000 px²
        min_area = img_area * MIN_AREA_FRAC
        max_area = img_area * MAX_AREA_FRAC
        ideal_area = img_area * IDEAL_AREA_FRAC

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # ── Stage 1: Color filtering ─────────────────────────────────
        # Batteries have metallic silver/grey/copper tones.
        # Silver/grey: low saturation, mid-to-high value
        # Widened: V floor lowered from 80→50 to catch dim lighting
        lower_silver = np.array([0, 0, 50])
        upper_silver = np.array([180, 70, 240])
        mask_silver = cv2.inRange(hsv, lower_silver, upper_silver)

        # Copper/gold top (positive terminal): warm hue, moderate saturation
        # Widened: V range 60-255 (was 80-230), S range expanded
        lower_copper = np.array([8, 30, 60])
        upper_copper = np.array([35, 220, 255])
        mask_copper = cv2.inRange(hsv, lower_copper, upper_copper)

        # Dark metallic body (Duracell-style dark green/black wrapper)
        # These are low-value, low-saturation dark regions
        lower_dark = np.array([0, 0, 25])
        upper_dark = np.array([180, 80, 90])
        mask_dark = cv2.inRange(hsv, lower_dark, upper_dark)

        # Combine metallic masks
        mask_metallic = cv2.bitwise_or(mask_silver, mask_copper)
        mask_metallic = cv2.bitwise_or(mask_metallic, mask_dark)

        # Exclude green areas (plants) from the search
        lower_green = np.array([30, 40, 40])
        upper_green = np.array([90, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)

        # Exclude brown (soil/dirt) — NARROWED to avoid eating battery copper
        # Reduced saturation range and value ceiling
        lower_brown = np.array([8, 80, 20])
        upper_brown = np.array([22, 200, 90])
        mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)

        # Final mask: metallic areas minus green/brown
        mask_exclude = cv2.bitwise_or(mask_green, mask_brown)
        mask = cv2.bitwise_and(mask_metallic, cv2.bitwise_not(mask_exclude))

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # ── Stage 2: Edge detection on masked region ─────────────────
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply mask to grayscale for edge detection
        gray_masked = cv2.bitwise_and(gray, gray, mask=mask)
        edges = cv2.Canny(gray_masked, 40, 120)

        # Also run edges on the full grayscale as backup
        edges_full = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)

        # Combine: masked edges + full edges within metallic mask
        edges_combined = cv2.bitwise_or(edges, cv2.bitwise_and(edges_full, mask))

        # Dilate to connect nearby edges
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges_combined = cv2.dilate(edges_combined, kernel_dilate, iterations=2)
        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges_combined = cv2.morphologyEx(edges_combined, cv2.MORPH_CLOSE,
                                           kernel_close, iterations=1)

        # ── Stage 3: Contour analysis ────────────────────────────────
        candidates = _score_battery_contours(
            edges_combined, mask, image,
            min_area, max_area, ideal_area,
            min_aspect, max_aspect, EXPECTED_ASPECT,
            h_img, w_img, use_metallic_score=True
        )

        # ── Stage 4: Fallback — pure shape detection (no color filter) ──
        # If color-based detection found nothing, try edge-only approach.
        # This catches batteries with unusual colors (black, dark blue, etc.)
        if not candidates:
            logger.info("Color-based detection found nothing, trying "
                         "shape-only fallback...")
            edges_shape = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 100)
            edges_shape = cv2.dilate(edges_shape, kernel_dilate, iterations=2)
            edges_shape = cv2.morphologyEx(edges_shape, cv2.MORPH_CLOSE,
                                            kernel_close, iterations=2)

            candidates = _score_battery_contours(
                edges_shape, mask, image,
                min_area, max_area, ideal_area,
                min_aspect, max_aspect, EXPECTED_ASPECT,
                h_img, w_img, use_metallic_score=False
            )

        if not candidates:
            logger.info("No battery candidates found after all detection stages")
            return None, 0.0

        # Return the best candidate
        candidates.sort(key=lambda c: c['score'], reverse=True)
        best = candidates[0]

        # Minimum confidence threshold — avoid false positives
        if best['score'] < 0.20:  # Lowered from 0.25 to catch more
            logger.info("Best battery candidate score %.3f below threshold 0.20, "
                         "rejecting", best['score'])
            return None, 0.0

        logger.info("Battery detected at %s (score=%.3f aspect=%.2f area=%d, "
                     "from %d candidates)",
                     best['bbox'], best['score'], best['aspect'],
                     best['area'], len(candidates))
        return best['bbox'], best['score']

    except Exception as exc:
        logger.exception("auto_detect_battery crashed: %s", exc)
        return None, 0.0


def _score_battery_contours(edges, mask, image,
                             min_area, max_area, ideal_area,
                             min_aspect, max_aspect, expected_aspect,
                             h_img, w_img, use_metallic_score=True):
    """Score contours from an edge map as battery candidates.

    Shared scoring logic used by both the color-filtered and
    shape-only detection stages.
    """
    import cv2
    import numpy as np
    import math

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)

    candidates = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        # Minimum bounding rectangle (rotated)
        rect = cv2.minAreaRect(contour)
        box_w, box_h = rect[1]

        if box_w < 5 or box_h < 5:
            continue

        # Ensure height > width for aspect ratio
        if box_w > box_h:
            box_w, box_h = box_h, box_w

        aspect = box_h / box_w

        if not (min_aspect <= aspect <= max_aspect):
            continue

        # Upright bounding rect
        x, y, w, h = cv2.boundingRect(contour)

        # ── Scoring ──────────────────────────────────────────────
        # Aspect ratio score (1.0 = perfect match)
        aspect_diff = abs(aspect - expected_aspect) / expected_aspect
        aspect_score = max(0.0, 1.0 - aspect_diff)

        # Size score (Gaussian around ideal area)
        if ideal_area > 0:
            log_ratio = math.log(area / ideal_area)
            size_score = math.exp(-0.5 * (log_ratio / 1.0) ** 2)
        else:
            size_score = 1.0

        # Rectangularity score (how rectangular is the contour?)
        rect_area = w * h
        if rect_area > 0:
            rectangularity = area / rect_area
        else:
            rectangularity = 0
        rect_score = min(1.0, rectangularity / 0.7)  # Normalize: 0.7+ = 1.0

        # Metallic pixel density within the bounding box
        if use_metallic_score:
            roi_mask = mask[y:y+h, x:x+w]
            if roi_mask.size > 0:
                metallic_ratio = np.count_nonzero(roi_mask) / roi_mask.size
            else:
                metallic_ratio = 0
            metallic_score = min(1.0, metallic_ratio / 0.3)  # 30%+ metallic = 1.0
        else:
            # Shape-only fallback: give a baseline metallic score
            metallic_score = 0.4

        # Combined score: weighted combination
        score = (aspect_score * 0.35 +
                 size_score * 0.20 +
                 rect_score * 0.20 +
                 metallic_score * 0.25)

        candidates.append({
            'bbox': (x, y, w, h),
            'score': score,
            'area': area,
            'aspect': aspect,
            'aspect_score': aspect_score,
            'size_score': size_score,
            'rect_score': rect_score,
            'metallic_score': metallic_score,
        })

        logger.debug("Battery candidate: bbox=(%d,%d,%d,%d) area=%d "
                     "aspect=%.2f scores=[asp=%.2f sz=%.2f rect=%.2f "
                     "metal=%.2f] total=%.3f",
                     x, y, w, h, area, aspect,
                     aspect_score, size_score, rect_score,
                     metallic_score, score)

    return candidates


def detect_and_calibrate(image_path, rotation=0, hflip=False, vflip=False,
                         depth_path=None):
    """Auto-detect an AA battery and compute calibration data.

    Detection priority:
      1. VLM (Jetson Orin AGX) — vision model that truly "sees" the battery
      2. OpenCV heuristics — color/shape fallback if VLM is unavailable

    Once found, calculates pixels_per_cm from the bbox vs known AA battery
    dimensions.  If ToF depth is available, also computes cross-validation.

    Returns a dict with battery detection results and calibration data.
    """
    result = {
        'battery_detected': False,
        'battery_bbox': None,
        'battery_confidence': 0.0,
        'pixels_per_cm': None,
        'plant_bbox': None,
        'ref_measurement': None,
        'tof_measurement': None,
        'detection_method': None,
    }

    try:
        image = _load_image(image_path, rotation, hflip, vflip)
    except (ValueError, FileNotFoundError) as exc:
        result['error'] = str(exc)
        return result

    h_img, w_img = image.shape[:2]

    # ── Detect battery (VLM first, then OpenCV fallback) ─────────
    detection_method = None
    battery_bbox_px, confidence = None, 0.0

    # Stage 1: Try VLM (Jetson Orin AGX vision model)
    try:
        battery_bbox_px, confidence = vlm_detect_battery(image)
        if battery_bbox_px is not None:
            detection_method = 'battery_vlm'
            logger.info("Battery found via VLM (confidence=%.2f)", confidence)
    except Exception as exc:
        logger.warning("VLM detection threw exception: %s", exc)

    # Stage 2: Fall back to OpenCV heuristics
    if battery_bbox_px is None:
        logger.info("VLM did not find battery, trying OpenCV fallback...")
        battery_bbox_px, confidence = auto_detect_battery(image)
        if battery_bbox_px is not None:
            detection_method = 'battery_auto'
            logger.info("Battery found via OpenCV (confidence=%.2f)",
                         confidence)

    if battery_bbox_px is None:
        return result

    bx, by, bw, bh = battery_bbox_px
    result['battery_detected'] = True
    result['battery_confidence'] = round(confidence, 3)
    result['battery_bbox'] = [
        int(by / h_img * 1000),           # ymin
        int(bx / w_img * 1000),           # xmin
        int((by + bh) / h_img * 1000),    # ymax
        int((bx + bw) / w_img * 1000),    # xmax
    ]

    # ── Calculate px/cm from battery ─────────────────────────────
    known = KNOWN_DIMENSIONS['aa_battery']
    # Match longer bbox dim to longer real dim
    bbox_long = max(bw, bh)
    bbox_short = min(bw, bh)
    ref_long = max(known['height_cm'], known['width_cm'])
    ref_short = min(known['height_cm'], known['width_cm'])

    if ref_long > 0 and bbox_long > 0:
        px_per_cm = bbox_long / ref_long
        result['pixels_per_cm'] = round(px_per_cm, 2)
        result['detection_method'] = detection_method or 'battery_auto'

    # ── Detect plant ─────────────────────────────────────────────
    plant_bbox_px = detect_plant_contour(image, exclude_bbox=battery_bbox_px)

    if plant_bbox_px:
        px, py, pw, ph = plant_bbox_px
        result['plant_bbox'] = [
            int(py / h_img * 1000),
            int(px / w_img * 1000),
            int((py + ph) / h_img * 1000),
            int((px + pw) / w_img * 1000),
        ]

        # ── Battery-based plant measurement ──────────────────────
        if result['pixels_per_cm'] and result['pixels_per_cm'] > 0:
            result['ref_measurement'] = {
                'height_cm': round(ph / result['pixels_per_cm'], 1),
                'width_cm': round(pw / result['pixels_per_cm'], 1),
            }

    # ── ToF cross-validation ─────────────────────────────────────
    tof_depth = load_tof_depth_grid(
        depth_path,
        target_shape=(h_img, w_img),
        rotation=rotation,
        hflip=hflip,
        vflip=vflip
    )

    if tof_depth is not None and plant_bbox_px:
        px, py, pw, ph = plant_bbox_px
        cx = min(px + pw // 2, w_img - 1)
        cy = min(py + ph // 2, h_img - 1)
        distance_mm = tof_depth[cy, cx]

        if 0 < distance_mm < 6000:
            w_cm, h_cm = calculate_physical_size(
                pw, ph, distance_mm, img_width=w_img, img_height=h_img
            )
            result['tof_measurement'] = {
                'height_cm': h_cm,
                'width_cm': w_cm,
                'distance_mm': round(float(distance_mm), 1),
            }

    return result


# ── Main measurement orchestrator ────────────────────────────────


def measure_objects(image_path, ref_type=None,
                    ref_width_cm=None, ref_height_cm=None,
                    rotation=0, hflip=False, vflip=False,
                    depth_path=None):
    """
    Detect plant, and compute real-world measurements using ToF data.

    Parameters:
        image_path:    Path to the captured image file
        ref_type:      Type of reference object (Legacy, mostly ignored if ToF is used)
        ref_width_cm:  Known width of reference object in cm (overrides default)
        ref_height_cm: Known height of reference object in cm (overrides default)
        rotation:      Image rotation (0, 90, 180, 270)
        hflip:         Horizontal flip
        vflip:         Vertical flip
        depth_path:    Path to the ToF depth map (.npy)

    Returns:
        dict with keys:
            success:            bool
            reference_bbox:     [ymin, xmin, ymax, xmax] in 0-1000 scale
            plant_bbox:         [ymin, xmin, ymax, xmax] in 0-1000 scale
            estimated_height_cm: float or None
            estimated_width_cm:  float or None
            pixels_per_cm:      float or None
            detection_method:   'tof_physical' | 'yolo' | 'opencv_contour' | None
            error:              str if success is False
    """
    result = {
        'success': False,
        'reference_bbox': None,
        'plant_bbox': None,
        'estimated_height_cm': None,
        'estimated_width_cm': None,
        'pixels_per_cm': None,
        'detection_method': None,
        'error': None,
    }

    try:
        image = _load_image(image_path, rotation, hflip, vflip)
    except (ValueError, FileNotFoundError) as exc:
        result['error'] = str(exc)
        return result

    h_img, w_img = image.shape[:2]

    # ── Step 1: Detect reference object ──────────────────────────
    ref_bbox_px = None  # (x, y, w, h) in pixels

    if ref_type:
        # Try YOLO first for COCO-class objects
        if ref_type in COCO_REFERENCE_MAP:
            ref_bbox_px = detect_reference_yolo(image, ref_type)
            if ref_bbox_px:
                result['detection_method'] = 'yolo'

        # Fall back to OpenCV contour detection
        if ref_bbox_px is None:
            ref_bbox_px = detect_reference_contour(image, ref_type)
            if ref_bbox_px:
                result['detection_method'] = 'opencv_contour'

    # ── Step 2: Detect plant ─────────────────────────────────────
    plant_bbox_px = detect_plant_contour(image, exclude_bbox=ref_bbox_px)

    # ── Step 3: Convert to normalized 0-1000 coordinates ─────────
    if ref_bbox_px:
        rx, ry, rw, rh = ref_bbox_px
        result['reference_bbox'] = [
            int(ry / h_img * 1000),          # ymin
            int(rx / w_img * 1000),           # xmin
            int((ry + rh) / h_img * 1000),    # ymax
            int((rx + rw) / w_img * 1000),    # xmax
        ]

    if plant_bbox_px:
        px, py, pw, ph = plant_bbox_px
        result['plant_bbox'] = [
            int(py / h_img * 1000),           # ymin
            int(px / w_img * 1000),           # xmin
            int((py + ph) / h_img * 1000),    # ymax
            int((px + pw) / w_img * 1000),    # xmax
        ]

    # ── Step 4: Calculate real-world dimensions ──────────────────
    
    # Load ToF depth map
    tof_depth = load_tof_depth_grid(
        depth_path,
        target_shape=(h_img, w_img),
        rotation=rotation,
        hflip=hflip,
        vflip=vflip
    )
    
    # ── ToF Math Strategy ──────────────────────────────────────────
    if tof_depth is not None and plant_bbox_px:
        # Use physical ToF distance mapping!
        px, py, pw, ph = plant_bbox_px
        
        # Sample the center of the plant bounding box
        cx = min(px + pw // 2, w_img - 1)
        cy = min(py + ph // 2, h_img - 1)
        
        # Get distance in mm
        distance_mm = tof_depth[cy, cx]
        logger.info("ToF distance at plant center (%d, %d): %.1f mm", cx, cy, distance_mm)
        
        if distance_mm > 0 and distance_mm < 6000:  # Ignore extreme outliers (>6m)
            w_cm, h_cm = calculate_physical_size(pw, ph, distance_mm, img_width=w_img, img_height=h_img)
            result['estimated_height_cm'] = h_cm
            result['estimated_width_cm'] = w_cm
            result['detection_method'] = 'tof_physical'
            
    # ── Legacy Reference Object Scaling Strategy ────────────────────
    if result['detection_method'] != 'tof_physical' and ref_bbox_px:
        # Use defaults from KNOWN_DIMENSIONS if not explicitly provided
        if ref_type and ref_type in KNOWN_DIMENSIONS:
            if ref_height_cm is None:
                ref_height_cm = KNOWN_DIMENSIONS[ref_type]['height_cm']
            if ref_width_cm is None:
                ref_width_cm = KNOWN_DIMENSIONS[ref_type]['width_cm']

        if ref_height_cm or ref_width_cm:
            _, _, rw, rh = ref_bbox_px

            # Match longer bbox dimension to longer reference dimension
            ref_long = max(ref_height_cm or 0, ref_width_cm or 0)
            ref_short = min(ref_height_cm or 0, ref_width_cm or 0)
            bbox_long = max(rw, rh)
            bbox_short = min(rw, rh)

            if ref_long > 0 and bbox_long > 0:
                px_per_cm_h = bbox_long / ref_long
            elif ref_short > 0 and bbox_short > 0:
                px_per_cm_h = bbox_short / ref_short
            else:
                px_per_cm_h = None

            if px_per_cm_h and px_per_cm_h > 0:
                result['pixels_per_cm'] = round(px_per_cm_h, 2)

                if plant_bbox_px:
                    _, _, pw, ph = plant_bbox_px
                    result['estimated_height_cm'] = round(ph / px_per_cm_h, 1)
                    result['estimated_width_cm'] = round(pw / px_per_cm_h, 1)

    if tof_depth is not None:
        result['depth_grid'] = generate_tof_depth_grid(tof_depth)

    result['success'] = True
    return result


def measure_with_manual_bbox(image_path, ref_bbox_norm, ref_type=None,
                              ref_width_cm=None, ref_height_cm=None,
                              rotation=0, hflip=False, vflip=False,
                              depth_path=None):
    """
    Measure using a manually-drawn bounding box (acting as the target object).

    With ToF enabled, the user can just draw a box around ANYTHING, 
    and we will instantly calculate its physical size without any reference battery!

    Parameters:
        image_path:    Path to the captured image file
        ref_bbox_norm: [ymin, xmin, ymax, xmax] in 0-1000 normalized scale
        ref_type:      Legacy reference type
        ref_width_cm:  Legacy known width
        ref_height_cm: Legacy known height
        rotation:      Image rotation (0, 90, 180, 270)
        hflip:         Horizontal flip
        vflip:         Vertical flip
        depth_path:    Path to the ToF depth map (.npy)

    Returns: dict with measurement results.
    """
    result = {
        'success': False,
        'reference_bbox': ref_bbox_norm,
        'plant_bbox': None,
        'estimated_height_cm': None,
        'estimated_width_cm': None,
        'pixels_per_cm': None,
        'detection_method': 'manual',
        'error': None,
    }

    try:
        image = _load_image(image_path, rotation, hflip, vflip)
    except (ValueError, FileNotFoundError) as exc:
        result['error'] = str(exc)
        return result

    h_img, w_img = image.shape[:2]

    # Convert normalized 0-1000 bbox to pixel coordinates
    ymin_n, xmin_n, ymax_n, xmax_n = ref_bbox_norm
    rx = int(xmin_n / 1000 * w_img)
    ry = int(ymin_n / 1000 * h_img)
    rw = int((xmax_n - xmin_n) / 1000 * w_img)
    rh = int((ymax_n - ymin_n) / 1000 * h_img)
    ref_bbox_px = (rx, ry, rw, rh)

    logger.info("Manual reference bbox: px=(%d,%d,%d,%d) from norm=%s",
                 rx, ry, rw, rh, ref_bbox_norm)

    # ── Auto-detect plant ────────────────────────────────────────
    plant_bbox_px = detect_plant_contour(image, exclude_bbox=ref_bbox_px)

    if plant_bbox_px:
        px, py, pw, ph = plant_bbox_px
        result['plant_bbox'] = [
            int(py / h_img * 1000),
            int(px / w_img * 1000),
            int((py + ph) / h_img * 1000),
            int((px + pw) / w_img * 1000),
        ]

    # ── ToF Math Strategy ──────────────────────────
    tof_depth = load_tof_depth_grid(
        depth_path,
        target_shape=(h_img, w_img),
        rotation=rotation,
        hflip=hflip,
        vflip=vflip
    )
    
    if tof_depth is not None:
        # User drew a box, and we have ToF. Treat the box as the object to measure!
        cx = rx + rw // 2
        cy = ry + rh // 2
        
        # Prevent out of bounds
        cx = min(cx, w_img - 1)
        cy = min(cy, h_img - 1)
        
        distance_mm = tof_depth[cy, cx]
        logger.info("ToF manual box center (%d, %d): %.1f mm", cx, cy, distance_mm)
        
        if distance_mm > 0 and distance_mm < 6000:
            w_cm, h_cm = calculate_physical_size(rw, rh, distance_mm, img_width=w_img, img_height=h_img)
            result['estimated_height_cm'] = h_cm
            result['estimated_width_cm'] = w_cm
            result['detection_method'] = 'tof_physical'
            
            # Since the user explicitly drew a box to measure, we can set the plant_bbox
            # equal to the reference_bbox so the frontend draws it properly.
            result['plant_bbox'] = ref_bbox_norm

    # ── Legacy Scaling Strategy (if ToF is missing) ────────────
    if result['detection_method'] != 'tof_physical':
        if ref_type and ref_type in KNOWN_DIMENSIONS:
            if ref_height_cm is None:
                ref_height_cm = KNOWN_DIMENSIONS[ref_type]['height_cm']
            if ref_width_cm is None:
                ref_width_cm = KNOWN_DIMENSIONS[ref_type]['width_cm']

        if (ref_height_cm or ref_width_cm) and rw > 0 and rh > 0:
            ref_long = max(ref_height_cm or 0, ref_width_cm or 0)
            ref_short = min(ref_height_cm or 0, ref_width_cm or 0)
            bbox_long = max(rw, rh)
            bbox_short = min(rw, rh)

            if ref_long > 0 and bbox_long > 0:
                px_per_cm = bbox_long / ref_long
            elif ref_short > 0 and bbox_short > 0:
                px_per_cm = bbox_short / ref_short
            else:
                px_per_cm = None

            if px_per_cm and px_per_cm > 0:
                result['pixels_per_cm'] = round(px_per_cm, 2)

                if plant_bbox_px:
                    _, _, pw, ph = plant_bbox_px
                    result['estimated_height_cm'] = round(ph / px_per_cm, 1)
                    result['estimated_width_cm'] = round(pw / px_per_cm, 1)

    if tof_depth is not None:
        result['depth_grid'] = generate_tof_depth_grid(tof_depth)

    result['success'] = True
    return result
