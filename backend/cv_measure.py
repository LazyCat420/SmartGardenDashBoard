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

# Directory where captured images are stored (same as camera_service)
CAPTURES_DIR = os.environ.get('CAPTURES_DIR', '/app/captures')

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
KNOWN_DIMENSIONS = {
    'soda_can':    {'height_cm': 12.2, 'width_cm': 6.6},
    'aa_battery':  {'height_cm': 5.0,  'width_cm': 1.4},
    'bic_lighter': {'height_cm': 8.0,  'width_cm': 2.5},
    'credit_card': {'height_cm': 5.4,  'width_cm': 8.56},
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


# ── Main measurement orchestrator ────────────────────────────────

def measure_objects(image_path, ref_type=None,
                    ref_width_cm=None, ref_height_cm=None,
                    rotation=0, hflip=False, vflip=False):
    """
    Detect reference object and plant, then compute real-world measurements.

    Parameters:
        image_path:    Path to the captured image file
        ref_type:      Type of reference object ('soda_can', 'aa_battery', etc.)
        ref_width_cm:  Known width of reference object in cm (overrides default)
        ref_height_cm: Known height of reference object in cm (overrides default)
        rotation:      Image rotation (0, 90, 180, 270)
        hflip:         Horizontal flip
        vflip:         Vertical flip

    Returns:
        dict with keys:
            success:            bool
            reference_bbox:     [ymin, xmin, ymax, xmax] in 0-1000 scale
            plant_bbox:         [ymin, xmin, ymax, xmax] in 0-1000 scale
            estimated_height_cm: float or None
            estimated_width_cm:  float or None
            pixels_per_cm:      float or None
            detection_method:   'yolo' | 'opencv_contour' | None
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
    # Use defaults from KNOWN_DIMENSIONS if not explicitly provided
    if ref_type and ref_type in KNOWN_DIMENSIONS:
        if ref_height_cm is None:
            ref_height_cm = KNOWN_DIMENSIONS[ref_type]['height_cm']
        if ref_width_cm is None:
            ref_width_cm = KNOWN_DIMENSIONS[ref_type]['width_cm']

    if ref_bbox_px and (ref_height_cm or ref_width_cm):
        _, _, rw, rh = ref_bbox_px

        if ref_height_cm and rh > 0:
            px_per_cm_h = rh / ref_height_cm
        elif ref_width_cm and rw > 0:
            px_per_cm_h = rw / ref_width_cm
        else:
            px_per_cm_h = None

        if px_per_cm_h and px_per_cm_h > 0:
            result['pixels_per_cm'] = round(px_per_cm_h, 2)

            if plant_bbox_px:
                _, _, pw, ph = plant_bbox_px
                result['estimated_height_cm'] = round(ph / px_per_cm_h, 1)
                result['estimated_width_cm'] = round(pw / px_per_cm_h, 1)

    result['success'] = True
    return result


def measure_with_manual_bbox(image_path, ref_bbox_norm, ref_type=None,
                              ref_width_cm=None, ref_height_cm=None,
                              rotation=0, hflip=False, vflip=False):
    """
    Measure using a manually-drawn reference bounding box.

    The user draws a box around the reference object in the UI.
    We skip auto-detection and use their bbox directly, then
    auto-detect the plant via green segmentation.

    Parameters:
        image_path:    Path to the captured image file
        ref_bbox_norm: [ymin, xmin, ymax, xmax] in 0-1000 normalized scale
        ref_type:      Type of reference object for known dimensions lookup
        ref_width_cm:  Known width in cm (overrides lookup)
        ref_height_cm: Known height in cm (overrides lookup)
        rotation:      Image rotation (0, 90, 180, 270)
        hflip:         Horizontal flip
        vflip:         Vertical flip

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

    # ── Calculate real-world dimensions ──────────────────────────
    if ref_type and ref_type in KNOWN_DIMENSIONS:
        if ref_height_cm is None:
            ref_height_cm = KNOWN_DIMENSIONS[ref_type]['height_cm']
        if ref_width_cm is None:
            ref_width_cm = KNOWN_DIMENSIONS[ref_type]['width_cm']

    if ref_height_cm or ref_width_cm:
        if ref_height_cm and rh > 0:
            px_per_cm = rh / ref_height_cm
        elif ref_width_cm and rw > 0:
            px_per_cm = rw / ref_width_cm
        else:
            px_per_cm = None

        if px_per_cm and px_per_cm > 0:
            result['pixels_per_cm'] = round(px_per_cm, 2)

            if plant_bbox_px:
                _, _, pw, ph = plant_bbox_px
                result['estimated_height_cm'] = round(ph / px_per_cm, 1)
                result['estimated_width_cm'] = round(pw / px_per_cm, 1)

    result['success'] = True
    return result
