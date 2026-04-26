from flask import Flask, Response, jsonify
import cv2
import threading
import time

app = Flask(__name__)

# Global camera object
camera = None
camera_lock = threading.Lock()

def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
        # Try to set decent resolution
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return camera

def generate_frames():
    while True:
        with camera_lock:
            cam = get_camera()
            success, frame = cam.read()
            if not success:
                break
            else:
                ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)  # ~10 FPS to save CPU

@app.route('/stream')
def video_stream():
    """Returns a continuous MJPEG video stream."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/snapshot')
def snapshot():
    """Returns a single JPEG snapshot."""
    with camera_lock:
        cam = get_camera()
        success, frame = cam.read()
        if not success:
            return jsonify({"error": "Failed to capture image"}), 500
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        return Response(buffer.tobytes(), mimetype='image/jpeg')

@app.route('/status')
def status():
    """Returns node status."""
    return jsonify({
        "status": "online",
        "device": "Raspberry Pi Camera Node",
        "resolution": "1280x720" if camera else "Not Initialized"
    })

if __name__ == '__main__':
    print("Starting Raspberry Pi Camera Node on port 5001...")
    # Run on all interfaces so the dashboard PC can access it
    app.run(host='0.0.0.0', port=5001, threaded=True)
