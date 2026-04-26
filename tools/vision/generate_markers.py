import cv2
import numpy as np
import os
import structlog

log = structlog.get_logger()

OUTPUT_DIR = "tools/vision/markers"

def generate_aruco_marker(marker_id: int = 0, marker_size_pixels: int = 400):
    """
    Generates an ArUco marker (DICT_4X4_50) which is standard and robust for simple tracking.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Define the dictionary
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    
    # Generate the marker
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size_pixels)
    
    # Save the marker
    output_path = os.path.join(OUTPUT_DIR, f"aruco_marker_id{marker_id}.png")
    cv2.imwrite(output_path, marker_img)
    log.info("aruco_marker_generated", path=output_path, marker_id=marker_id, size=marker_size_pixels)
    return output_path

def generate_checkerboard(cols: int = 9, rows: int = 6, square_size_pixels: int = 100):
    """
    Generates a standard checkerboard pattern for intrinsic camera calibration.
    Note: cols and rows refer to the number of *inner corners*.
    So a 9x6 inner corner board has 10 squares horizontally and 7 squares vertically.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    width = (cols + 1) * square_size_pixels
    height = (rows + 1) * square_size_pixels
    
    # Create white canvas
    board_img = np.ones((height, width), dtype=np.uint8) * 255
    
    # Draw the black squares
    for i in range(height // square_size_pixels):
        for j in range(width // square_size_pixels):
            if (i + j) % 2 == 0:
                y1 = i * square_size_pixels
                y2 = (i + 1) * square_size_pixels
                x1 = j * square_size_pixels
                x2 = (j + 1) * square_size_pixels
                board_img[y1:y2, x1:x2] = 0
                
    output_path = os.path.join(OUTPUT_DIR, f"checkerboard_{cols}x{rows}.png")
    cv2.imwrite(output_path, board_img)
    log.info("checkerboard_generated", path=output_path, cols=cols, rows=rows, square_size=square_size_pixels)
    return output_path

if __name__ == "__main__":
    log.info("generating_vision_markers")
    generate_aruco_marker(marker_id=0, marker_size_pixels=500)
    generate_checkerboard(cols=9, rows=6, square_size_pixels=100)
    log.info("marker_generation_complete", output_dir=OUTPUT_DIR)
    print(f"Markers generated successfully in {OUTPUT_DIR}!")
    print("Please print these on standard 8.5x11 paper for calibration.")
