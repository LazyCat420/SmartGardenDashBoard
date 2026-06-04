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


def ensure_captures_dir():
    """Ensure the captures directory exists."""
    os.makedirs(CAPTURES_DIR, exist_ok=True)


def test_connection(ssh_host, ssh_user='pi', ssh_port=22):
    """Test SSH connectivity to a Pi endpoint.

    Returns dict with 'reachable' bool and 'message' string.
    """
    cmd = [
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        '-o', 'BatchMode=yes',
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
        if result.returncode == 0 and 'OK' in result.stdout:
            return {'reachable': True, 'message': 'Connection successful'}
        return {
            'reachable': False,
            'message': f'SSH failed (exit {result.returncode}): {result.stderr.strip()}'
        }
    except subprocess.TimeoutExpired:
        return {'reachable': False, 'message': 'Connection timed out after 15s'}
    except FileNotFoundError:
        return {'reachable': False, 'message': 'SSH client not installed in container'}
    except Exception as e:
        return {'reachable': False, 'message': str(e)}


def capture_image(ssh_host, ssh_user='pi', ssh_port=22,
                  capture_command='rpicam-still -o - --width 1920 --height 1080 -t 1000',
                  endpoint_id=None):
    """Capture an image from a Pi camera via SSH.

    The capture_command must output the image to stdout (using -o -).
    Returns dict with 'success', 'image_path', 'filename', and 'message'.
    """
    ensure_captures_dir()

    # Generate a unique filename using UUID to prevent path traversal
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    filename = f'{timestamp}_{endpoint_id or "unknown"}_{unique_id}.jpg'
    image_path = os.path.join(CAPTURES_DIR, filename)

    # Validate the resolved path stays within CAPTURES_DIR
    resolved = os.path.realpath(image_path)
    if not resolved.startswith(os.path.realpath(CAPTURES_DIR) + os.sep):
        return {'success': False, 'message': 'Invalid capture path'}

    cmd = [
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        '-o', 'BatchMode=yes',
        '-p', str(ssh_port),
        f'{ssh_user}@{ssh_host}',
        capture_command
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            stderr_text = result.stderr.decode('utf-8', errors='replace').strip()
            return {
                'success': False,
                'message': f'Capture failed (exit {result.returncode}): {stderr_text}'
            }

        if not result.stdout or len(result.stdout) < 100:
            return {
                'success': False,
                'message': 'Capture returned empty or too-small image data'
            }

        # Validate the image looks like a JPEG (magic bytes check)
        if not result.stdout[:2] == b'\xff\xd8':
            return {
                'success': False,
                'message': 'Captured data does not appear to be a valid JPEG image'
            }

        # Write the image to disk
        with open(resolved, 'wb') as f:
            f.write(result.stdout)

        logger.info('Captured image: %s (%d bytes)', filename, len(result.stdout))

        return {
            'success': True,
            'image_path': resolved,
            'filename': filename,
            'size_bytes': len(result.stdout),
            'message': f'Captured {len(result.stdout)} bytes'
        }

    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Capture timed out after 30s'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def analyze_image(image_path, plant_name=None, plant_variety=None,
                  last_height=None, llm_url=None, llm_model=None):
    """Send a captured image to the vision LLM for plant analysis.

    Returns dict with analysis results or error.
    """
    if not llm_url:
        llm_url = os.environ.get(
            'LLM_SERVICE_URL',
            'http://localhost:1234/v1/chat/completions'
        )
    if not llm_model:
        llm_model = os.environ.get(
            'LLM_MODEL_NAME',
            'ibm-granite/granite-3.3-8b-instruct'
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

    prompt = f"""Analyze this garden plant image. Return ONLY a valid JSON object with these fields:
{{
  "plant_species": "identified species name or null if unclear",
  "confidence": 0.0 to 1.0,
  "estimated_height_cm": number or null,
  "estimated_width_cm": number or null,
  "health_rating": 1 to 10,
  "health_notes": "brief description of plant health",
  "pests_detected": [{{"type": "pest name", "severity": "mild|moderate|severe"}}],
  "growth_stage": "seedling|vegetative|flowering|fruiting|mature",
  "recommendations": ["list of care recommendations"]
}}

Plant context: {plant_context}

Important: Return ONLY the JSON object, no markdown, no explanation."""

    payload = {
        'model': llm_model,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{image_b64}'
                        }
                    }
                ]
            }
        ],
        'max_tokens': 1024,
        'temperature': 0.1
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

    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        response = http_requests.post(
            llm_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        # Extract the response text
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Try to parse JSON from the response
        # Strip markdown code fences if present
        clean = content.strip()
        if clean.startswith('```'):
            lines = clean.split('\n')
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.strip().startswith('```')]
            clean = '\n'.join(lines)

        analysis = json.loads(clean)
        return {'success': True, 'analysis': analysis}

    except json.JSONDecodeError:
        logger.warning('Vision LLM returned non-JSON response: %s', content[:200])
        return {
            'success': False,
            'error': 'Vision model returned non-JSON response',
            'raw_response': content[:500]
        }
    except http_requests.exceptions.Timeout:
        return {'success': False, 'error': 'Vision analysis timed out (120s)'}
    except http_requests.exceptions.ConnectionError:
        return {'success': False, 'error': 'Cannot connect to LLM service'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
