"""
Camera Service — SSH-based camera capture from Raspberry Pi endpoints.

Captures images by SSHing into the Pi and running rpicam-still,
then pipes the image back to the NAS container for storage and analysis.
"""

import subprocess
import os
import uuid
import base64
import json
import logging
from datetime import datetime

import requests as http_requests

logger = logging.getLogger(__name__)

# Directory for captured images (volume-mounted in Docker)
CAPTURES_DIR = os.environ.get('CAPTURES_DIR', '/app/captures')

# Common SSH options used by all SSH/SCP commands.
# UserKnownHostsFile=/dev/null prevents write failures when the
# container's ~/.ssh directory is mounted read-only.
SSH_OPTS = [
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'UserKnownHostsFile=/dev/null',
    '-o', 'ConnectTimeout=10',
    '-o', 'BatchMode=yes',
    '-o', 'LogLevel=ERROR',
]


def ensure_captures_dir():
    """Ensure the captures directory exists."""
    os.makedirs(CAPTURES_DIR, exist_ok=True)


def test_connection(ssh_host, ssh_user='pi', ssh_port=22):
    """Test SSH connectivity AND camera availability on a Pi endpoint.

    Two-phase test:
      1. SSH connectivity — runs 'echo OK'
      2. Camera check — runs 'libcamera-hello --list-cameras' to see if
         the camera hardware is registered with libcamera.

    Returns dict with 'reachable' bool, 'camera_available' bool, and 'message' string.
    """
    # Phase 1: SSH connectivity
    cmd = [
        'ssh', *SSH_OPTS,
        '-p', str(ssh_port),
        f'{ssh_user}@{ssh_host}',
        'echo OK'
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode != 0 or 'OK' not in result.stdout:
            return {
                'reachable': False,
                'camera_available': False,
                'message': f'SSH failed (exit {result.returncode}): {result.stderr.strip()}'
            }
    except subprocess.TimeoutExpired:
        return {'reachable': False, 'camera_available': False, 'message': 'Connection timed out after 15s'}
    except FileNotFoundError:
        return {'reachable': False, 'camera_available': False, 'message': 'SSH client not installed in container'}
    except Exception as e:
        return {'reachable': False, 'camera_available': False, 'message': str(e)}

    # Phase 2: Camera availability check
    cam_cmd = [
        'ssh', *SSH_OPTS,
        '-p', str(ssh_port),
        f'{ssh_user}@{ssh_host}',
        'libcamera-hello --list-cameras 2>&1 || rpicam-hello --list-cameras 2>&1 || echo NO_CAMERAS'
    ]
    try:
        cam_result = subprocess.run(
            cam_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        cam_output = cam_result.stdout.strip() + cam_result.stderr.strip()
        has_camera = (
            'no cameras available' not in cam_output.lower()
            and 'NO_CAMERAS' not in cam_output
            and cam_result.returncode == 0
        )
        if has_camera:
            return {
                'reachable': True,
                'camera_available': True,
                'message': 'SSH connected — camera detected'
            }
        else:
            return {
                'reachable': True,
                'camera_available': False,
                'message': ('SSH connected but NO CAMERA detected. '
                            'The Pi may need a reboot or the camera driver '
                            'needs to be reloaded. Try the "Reinitialize Camera" button.')
            }
    except Exception:
        # Camera check failed but SSH is fine
        return {
            'reachable': True,
            'camera_available': None,
            'message': 'SSH connected — could not verify camera status'
        }


def reinitialize_camera(ssh_host, ssh_user='pi', ssh_port=22):
    """Remotely reinitialize the camera subsystem on a Pi.

    After a Pi reboot the ArduCam Pivariety driver sometimes fails to
    register.  This function SSHes in and reloads the relevant kernel
    modules / restarts the libcamera service so the camera comes back.

    Returns dict with 'success' bool and 'message'/'output' strings.
    """
    # Chain of commands to reload the camera stack:
    #   1. Unload and reload the arducam module (if present)
    #   2. Restart the libcamera-related services
    #   3. Quick verify with rpicam-hello / libcamera-hello
    reinit_script = (
        'set -e; '
        'echo "=== Reloading camera modules ==="; '
        'sudo modprobe -r arducam_pivariety 2>/dev/null || true; '
        'sudo modprobe arducam_pivariety 2>/dev/null || true; '
        'sudo modprobe -r imx708 2>/dev/null || true; '
        'sudo modprobe imx708 2>/dev/null || true; '
        'sleep 2; '
        'echo "=== Checking camera availability ==="; '
        'rpicam-hello --list-cameras 2>&1 || libcamera-hello --list-cameras 2>&1 || echo "NO_CAMERAS_FOUND"'
    )

    cmd = [
        'ssh', *SSH_OPTS,
        '-p', str(ssh_port),
        f'{ssh_user}@{ssh_host}',
        reinit_script
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout.strip()
        stderr = result.stderr.strip()

        if 'NO_CAMERAS_FOUND' in output:
            return {
                'success': False,
                'message': ('Camera modules reloaded but still no camera detected. '
                            'Try physically reseating the camera cable and rebooting the Pi.'),
                'output': output + '\n' + stderr
            }

        if result.returncode != 0:
            return {
                'success': False,
                'message': f'Reinitialize failed (exit {result.returncode})',
                'output': output + '\n' + stderr
            }

        return {
            'success': True,
            'message': 'Camera modules reloaded successfully',
            'output': output
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Reinitialize timed out after 30s'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def capture_image(ssh_host, ssh_user='pi', ssh_port=22,
                  capture_command='~/tof_env/bin/python ~/capture_rgbd.py',
                  endpoint_id=None):
    """Capture an image from a Pi camera via SSH.

    Runs the capture_rgbd.py script on the Pi to generate image.jpg and depth.npy,
    then copies both files back to the NAS.
    Returns dict with 'success', 'image_path', 'depth_path', 'filename', and 'message'.
    """
    ensure_captures_dir()

    # Generate a unique filename using UUID to prevent path traversal
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    filename = f'{timestamp}_{endpoint_id or "unknown"}_{unique_id}'
    image_path = os.path.join(CAPTURES_DIR, f"{filename}.jpg")
    depth_path = os.path.join(CAPTURES_DIR, f"{filename}_depth.npy")

    # Validate the resolved path stays within CAPTURES_DIR
    resolved_img = os.path.realpath(image_path)
    resolved_depth = os.path.realpath(depth_path)
    cap_dir_real = os.path.realpath(CAPTURES_DIR) + os.sep
    if not resolved_img.startswith(cap_dir_real) or not resolved_depth.startswith(cap_dir_real):
        return {'success': False, 'message': 'Invalid capture path'}

    # Ensure capture_rgbd.py on the Pi matches the latest in the container
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(backend_dir)
    local_script_path = os.path.join(root_dir, 'capture_rgbd.py')
    if not os.path.exists(local_script_path):
        local_script_path = '/app/capture_rgbd.py'

    if os.path.exists(local_script_path):
        cmd_scp_script = [
            'scp',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-P', str(ssh_port),
            local_script_path,
            f'{ssh_user}@{ssh_host}:~/capture_rgbd.py'
        ]
        try:
            logger.info("Syncing latest capture_rgbd.py to Pi %s...", ssh_host)
            subprocess.run(cmd_scp_script, check=True, timeout=10)
        except Exception as e:
            logger.warning("Failed to sync capture_rgbd.py to Pi: %s", e)

    cmd_trigger = [
        'ssh', *SSH_OPTS,
        '-p', str(ssh_port),
        f'{ssh_user}@{ssh_host}',
        capture_command
    ]

    try:
        # Trigger the dual capture script on the Pi
        result = subprocess.run(cmd_trigger, capture_output=True, timeout=45)

        if result.returncode != 0:
            stderr_text = result.stderr.decode('utf-8', errors='replace').strip()
            return {
                'success': False,
                'message': f'Capture failed (exit {result.returncode}): {stderr_text}'
            }

        # Copy the image.jpg file back
        cmd_scp_img = [
            'scp',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-P', str(ssh_port),
            f'{ssh_user}@{ssh_host}:~/image.jpg',
            resolved_img
        ]
        subprocess.run(cmd_scp_img, check=True)

        # Copy the depth.npy file back
        cmd_scp_depth = [
            'scp',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'LogLevel=ERROR',
            '-P', str(ssh_port),
            f'{ssh_user}@{ssh_host}:~/depth.npy',
            resolved_depth
        ]
        try:
            subprocess.run(cmd_scp_depth, check=True)
            has_depth = True
        except subprocess.CalledProcessError:
            has_depth = False
            logger.warning("depth.npy not found on Pi, proceeding without ToF depth.")

        # Copy the confidence.npy file back (non-fatal if missing)
        confidence_path = os.path.join(CAPTURES_DIR, f"{filename}_confidence.npy")
        resolved_conf = os.path.realpath(confidence_path)
        if resolved_conf.startswith(cap_dir_real):
            cmd_scp_conf = [
                'scp',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'LogLevel=ERROR',
                '-P', str(ssh_port),
                f'{ssh_user}@{ssh_host}:~/confidence.npy',
                resolved_conf
            ]
            try:
                subprocess.run(cmd_scp_conf, check=True)
                logger.info("Copied confidence.npy for capture %s", filename)
            except subprocess.CalledProcessError:
                logger.debug("confidence.npy not found on Pi (older capture script?).")

        # Read size for logging
        size_bytes = os.path.getsize(resolved_img)
        logger.info('Captured image: %s.jpg (%d bytes)', filename, size_bytes)

        return {
            'success': True,
            'image_path': resolved_img,
            'depth_path': resolved_depth if has_depth else None,
            'filename': filename,
            'size_bytes': size_bytes,
            'message': f'Captured {size_bytes} bytes'
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Capture timed out after 45s'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def load_projects_json():
    """Dynamically load projects.json config, searching direct paths and parent directories."""
    # 1. Check direct path /app/projects.json (mounted in container)
    p_direct = "/app/projects.json"
    if os.path.isfile(p_direct):
        try:
            with open(p_direct, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # 2. Walk up parent directories (like trading-service)
    from pathlib import Path
    curr = Path(__file__).resolve()
    for parent in curr.parents:
        p1 = parent / "vault-service" / "projects.json"
        if p1.is_file():
            try:
                with open(p1, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        p2 = parent / "projects.json"
        if p2.is_file():
            try:
                with open(p2, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

def get_prism_settings():
    """Retrieve Prism URL, project, and username from projects.json or environment."""
    projects_data = load_projects_json()
    config = projects_data.get("config", {})
    default_host = projects_data.get("defaultHost", "10.0.0.16")
    
    prism_url = os.environ.get("PRISM_URL") or config.get("PRISM_URL") or f"http://{default_host}:7778"
    # Attribution: this is the garden dashboard, not the trading bot. Deliberately
    # NOT read from projects.json — its shared PRISM_PROJECT is "vllm-trading-bot"
    # for every repo, which filed garden vision calls under the trading project.
    prism_project = os.environ.get("PRISM_PROJECT") or "smart-garden"
    prism_username = os.environ.get("PRISM_USERNAME") or "admin"
    
    return prism_url, prism_project, prism_username


def transform_image(image_data, rotation=0, hflip=False, vflip=False):
    """Rotate and flip image data using Pillow."""
    if not (rotation or hflip or vflip):
        return image_data
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_data))
        
        # Apply flips
        if hflip:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if vflip:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
        # Apply rotation (clockwise)
        # Note: PIL ROTATE_90 is counter-clockwise, so to rotate clockwise:
        # 90 clockwise = ROTATE_270
        # 180 clockwise = ROTATE_180
        # 270 clockwise = ROTATE_90
        if rotation == 90:
            img = img.transpose(Image.ROTATE_270)
        elif rotation == 180:
            img = img.transpose(Image.ROTATE_180)
        elif rotation == 270:
            img = img.transpose(Image.ROTATE_90)
            
        out_buf = io.BytesIO()
        img.save(out_buf, format='JPEG')
        return out_buf.getvalue()
    except Exception as e:
        logger.warning(f"Failed to transform image for LLM: {e}")
        return image_data


def analyze_image(image_path, plant_name=None, plant_variety=None,
                  last_height=None, llm_url=None, llm_model=None,
                  rotation=0, hflip=False, vflip=False,
                  ref_width_cm=None, ref_height_cm=None,
                  reference_type=None, depth_path=None,
                  offset_x_mm=None, offset_y_mm=None, distance_offset_mm=None):
    """Analyze a captured plant image using YOLO/OpenCV for measurement
    and the Vision LLM for health/species analysis.

    Phase 1 — Measurement (YOLO + OpenCV + ToF Depth):
        Detects the reference object and plant, computes bounding boxes
        and real-world cm dimensions using physical ToF laser distance.

    Phase 2 — Health Analysis (Vision LLM):
        Sends the image to the LLM for species ID, health rating,
        growth stage, pest detection, and care recommendations.
        The LLM is NOT asked for bounding boxes or measurements.

    Returns dict with 'success' and merged 'analysis' results.
    """

    # ── Phase 1: YOLO + OpenCV + ToF Measurement ───────────────────────
    measurement = {'success': False}
    try:
        from backend.cv_measure import measure_objects
        measurement = measure_objects(
            image_path=image_path,
            ref_type=reference_type,
            ref_width_cm=ref_width_cm,
            ref_height_cm=ref_height_cm,
            rotation=rotation,
            hflip=hflip,
            vflip=vflip,
            depth_path=depth_path,
            offset_x_mm=offset_x_mm,
            offset_y_mm=offset_y_mm,
            distance_offset_mm=distance_offset_mm
        )
        logger.info("CV measurement result: success=%s method=%s height=%s width=%s",
                     measurement.get('success'),
                     measurement.get('detection_method'),
                     measurement.get('estimated_height_cm'),
                     measurement.get('estimated_width_cm'))
    except Exception as exc:
        logger.warning("CV measurement failed, continuing with LLM only: %s", exc)

    # ── Phase 2: Vision LLM Health Analysis ──────────────────────
    prism_url, prism_project, prism_username = get_prism_settings()

    if not llm_url:
        llm_url = os.environ.get("LLM_SERVICE_URL") or f"{prism_url}/chat?stream=false"
    elif "/v1/chat/completions" in llm_url:
        if "7777" in llm_url:
            llm_url = llm_url.replace("/v1/chat/completions", "/chat?stream=false")

    if not llm_model:
        llm_model = os.environ.get(
            'LLM_MODEL_NAME',
            'qwen3.6'
        )

    # Read and base64-encode the image
    resolved = os.path.realpath(image_path)
    if not resolved.startswith(os.path.realpath(CAPTURES_DIR) + os.sep):
        return {'success': False, 'error': 'Invalid image path'}

    try:
        with open(resolved, 'rb') as f:
            image_data = f.read()
    except FileNotFoundError:
        return {'success': False, 'error': 'Image file not found'}

    # Impose a 10MB size limit for analysis
    if len(image_data) > 10 * 1024 * 1024:
        return {'success': False, 'error': 'Image too large for analysis (>10MB)'}

    # Transform image for LLM if rotation/flip settings are specified
    if rotation or hflip or vflip:
        image_data = transform_image(image_data, rotation, hflip, vflip)

    image_b64 = base64.b64encode(image_data).decode('utf-8')

    # Build context about the plant if available
    context_parts = []
    if plant_name:
        context_parts.append(f'Known plant name: {plant_name}')
    if plant_variety:
        context_parts.append(f'Variety: {plant_variety}')
    if last_height is not None:
        context_parts.append(f'Last recorded height: {last_height}cm')

    plant_context = '. '.join(context_parts) if context_parts else 'No prior plant information available.'

    # Simplified prompt — NO bounding box or measurement instructions.
    # YOLO/OpenCV handles all spatial detection; the LLM focuses on
    # what it is good at: understanding the plant.
    prompt = f"""Analyze this garden plant image. Return ONLY a valid JSON object with these fields:
{{
  "plant_species": "identified species name or null if unclear",
  "confidence": 0.0 to 1.0,
  "health_rating": 1 to 10,
  "health_notes": "brief description of plant health",
  "pests_detected": [{{"type": "pest name", "severity": "mild|moderate|severe"}}],
  "growth_stage": "seedling|vegetative|flowering|fruiting|mature",
  "recommendations": ["list of care recommendations"]
}}

Plant context: {plant_context}

Important: Return ONLY the JSON object, no markdown, no explanation."""

    # Format payload for Prism /chat
    payload = {
        'provider': 'vllm',
        'model': llm_model,
        'messages': [
            {
                'role': 'user',
                'content': prompt,
                'images': [
                    f'data:image/jpeg;base64,{image_b64}'
                ]
            }
        ],
        'maxTokens': 2048,
        'temperature': 0.1,
        'thinkingEnabled': False,
        'conversationId': str(uuid.uuid4()),
        'project': prism_project,
        'username': prism_username
    }

    headers = {
        'Content-Type': 'application/json',
        'x-project': prism_project,
        'x-username': prism_username
    }

    # Load API key if available
    api_key = ''
    try:
        settings_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json'
        )
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                api_key = settings.get('api_key', '')
    except Exception:
        pass

    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        logger.info("Sending health analysis request to %s for model %s...",
                     llm_url, llm_model)
        response = http_requests.post(
            llm_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        # Extract the response text from Prism format
        response_data = data.get('response')
        if isinstance(response_data, dict):
            data = response_data

        content = data.get('text') or data.get('content') or ''
        if not content and 'choices' in data:
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Parse JSON from the response
        clean = content.strip()
        if clean.startswith('```'):
            lines = clean.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            clean = '\n'.join(lines)

        analysis = json.loads(clean)

    except json.JSONDecodeError:
        logger.warning('Vision LLM returned non-JSON response: %s', content[:200])
        # If LLM fails but we have measurement data, return measurement-only
        if measurement.get('success'):
            analysis = {
                'plant_species': None,
                'confidence': None,
                'health_rating': None,
                'health_notes': 'LLM analysis failed — measurement data only',
                'pests_detected': [],
                'growth_stage': None,
                'recommendations': [],
            }
        else:
            return {
                'success': False,
                'error': 'Vision model returned non-JSON response',
                'raw_response': content[:500]
            }
    except http_requests.exceptions.Timeout:
        if measurement.get('success'):
            analysis = {
                'plant_species': None, 'confidence': None,
                'health_rating': None,
                'health_notes': 'LLM timed out — measurement data only',
                'pests_detected': [], 'growth_stage': None,
                'recommendations': [],
            }
        else:
            return {'success': False, 'error': f'Vision analysis timed out (120s) at {llm_url}'}
    except http_requests.exceptions.ConnectionError:
        if measurement.get('success'):
            analysis = {
                'plant_species': None, 'confidence': None,
                'health_rating': None,
                'health_notes': 'Cannot connect to LLM — measurement data only',
                'pests_detected': [], 'growth_stage': None,
                'recommendations': [],
            }
        else:
            return {'success': False, 'error': f'Cannot connect to LLM service at {llm_url}'}
    except Exception as e:
        if measurement.get('success'):
            analysis = {
                'plant_species': None, 'confidence': None,
                'health_rating': None,
                'health_notes': f'LLM error: {e} — measurement data only',
                'pests_detected': [], 'growth_stage': None,
                'recommendations': [],
            }
        else:
            return {'success': False, 'error': str(e)}

    # ── Merge measurement results into analysis ──────────────────
    if measurement.get('success'):
        analysis['reference_bbox'] = measurement.get('reference_bbox')
        analysis['plant_bbox'] = measurement.get('plant_bbox')
        analysis['estimated_height_cm'] = measurement.get('estimated_height_cm')
        analysis['estimated_width_cm'] = measurement.get('estimated_width_cm')
        analysis['calculated_height_cm'] = measurement.get('estimated_height_cm')
        analysis['calculated_width_cm'] = measurement.get('estimated_width_cm')
        analysis['pixels_per_cm'] = measurement.get('pixels_per_cm')
        analysis['detection_method'] = measurement.get('detection_method')
        analysis['reference_object_detected'] = reference_type
    else:
        # No CV measurement — set empty values so frontend doesn't break
        analysis.setdefault('reference_bbox', None)
        analysis.setdefault('plant_bbox', None)
        analysis.setdefault('estimated_height_cm', None)
        analysis.setdefault('estimated_width_cm', None)
        analysis.setdefault('detection_method', None)

    return {'success': True, 'analysis': analysis}

