"""
Smart Garden Dashboard - Main API Server
Using Markdown files for Obsidian-compatible storage
"""

from flask import Flask, request, jsonify, send_file, redirect, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import json
import os
import requests
import qrcode
from qrcode.constants import ERROR_CORRECT_L
import io
import base64

# Import MD service
from md_service import (
    ensure_directories, get_storage_path,
    # Plants
    create_plant, get_plant, get_plant_by_code, list_plants, update_plant, delete_plant,
    get_next_instance_number,
    # Logs
    create_growth_log, get_growth_logs,
    create_watering, get_waterings, get_all_waterings,
    create_fertilization, get_fertilizations,
    create_harvest, get_harvests,
    create_pest_issue, get_pest_issues,
    # Tasks
    create_task, get_task, list_tasks, complete_task, delete_task,
    # Weather
    create_weather_log, list_weather_logs,
    # Notes
    create_note, list_notes, update_note,
    # Recipes
    create_recipe, get_recipe, list_recipes, update_recipe, delete_recipe,
    # Budget
    create_product, get_product, list_products, update_product, delete_product,
    get_budget_summary, get_cost_per_plant,
    # Charts
    get_growth_chart_data, get_watering_chart_data, get_budget_chart_data
)

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)


# ============== LLM Configuration ==============

LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "ibm-granite/granite-3.3-8b-instruct"

GARDEN_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_plant",
            "description": "Add a new plant to the garden. Use when the user mentions planting something new.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The name of the plant"},
                    "variety": {"type": "string", "description": "The specific variety"},
                    "location": {"type": "string", "description": "Where the plant is located"},
                    "date_planted": {"type": "string", "description": "Date planted (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Additional notes"},
                    "quantity": {"type": "integer", "description": "Number of plants to add"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_watering",
            "description": "Log a watering event for a plant. Can include compost tea recipes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "amount_ml": {"type": "number", "description": "Amount in ml"},
                    "amount_value": {"type": "number", "description": "Amount in other units"},
                    "amount_unit": {"type": "string", "description": "Unit (ml, gallons, cups)"},
                    "method": {"type": "string", "description": "Watering method (watering can, hose, compost tea, spray, soak)"},
                    "recipe_name": {"type": "string", "description": "Name of compost tea recipe used"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_fertilization",
            "description": "Log a fertilization event for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "fertilizer_type": {"type": "string", "description": "Type of fertilizer"},
                    "amount": {"type": "string", "description": "Amount applied (e.g., '2 tbsp', '1 cup')"},
                    "npk_ratio": {"type": "string", "description": "NPK ratio (e.g., '10-10-10')"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name", "fertilizer_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_harvest",
            "description": "Log a harvest from a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "quantity": {"type": "number", "description": "Amount harvested"},
                    "unit": {"type": "string", "description": "Unit (kg, lbs, pieces, bunches)"},
                    "quality_rating": {"type": "integer", "description": "Quality 1-10"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_growth",
            "description": "Log growth measurements for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "height_cm": {"type": "number", "description": "Height in cm"},
                    "width_cm": {"type": "number", "description": "Width in cm"},
                    "leaf_count": {"type": "integer", "description": "Number of leaves"},
                    "health_rating": {"type": "integer", "description": "Health 1-10"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "report_pest_issue",
            "description": "Report a pest or disease issue for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Affected plant"},
                    "pest_type": {"type": "string", "description": "Type of pest/disease"},
                    "severity": {"type": "string", "description": "mild, moderate, or severe"},
                    "treatment": {"type": "string", "description": "Treatment applied"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name", "pest_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a garden task or reminder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "task_type": {"type": "string", "description": "watering, fertilizing, pruning, harvesting, planting, pest_control, maintenance, other"},
                    "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                    "priority": {"type": "string", "description": "low, medium, high"},
                    "description": {"type": "string", "description": "Task details"},
                    "recurring": {"type": "boolean", "description": "Is this recurring?"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_weather",
            "description": "Log weather conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "temperature_high": {"type": "number", "description": "High temp"},
                    "temperature_low": {"type": "number", "description": "Low temp"},
                    "humidity": {"type": "number", "description": "Humidity %"},
                    "rainfall_mm": {"type": "number", "description": "Rainfall mm"},
                    "conditions": {"type": "string", "description": "sunny, cloudy, rainy, etc."},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_plant_status",
            "description": "Update a plant's status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "status": {"type": "string", "description": "active, harvested, or removed"}
                },
                "required": ["plant_name", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_budget_item",
            "description": "Add a product/nutrient to budget tracking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Product name"},
                    "brand": {"type": "string", "description": "Brand name"},
                    "category": {"type": "string", "description": "fertilizer, amendment, pesticide, tool, seed, other"},
                    "size_amount": {"type": "number", "description": "Package size amount"},
                    "size_unit": {"type": "string", "description": "oz, lb, gallon, each"},
                    "purchase_price": {"type": "number", "description": "Purchase price"},
                    "npk_ratio": {"type": "string", "description": "NPK if applicable"},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["name", "purchase_price"]
            }
        }
    }
]


# ============== Helper Functions ==============

def find_plant_by_name(name):
    """Find a plant by name (fuzzy match)"""
    plants = list_plants()
    name_lower = name.lower()
    
    # Try exact match first
    for p in plants:
        if p.get('name', '').lower() == name_lower:
            return p
        if p.get('display_name', '').lower() == name_lower:
            return p
    
    # Try partial match
    for p in plants:
        if name_lower in p.get('name', '').lower():
            return p
        if name_lower in p.get('display_name', '').lower():
            return p
    
    return None


# ============== Static Files ==============

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')


# ============== LLM Endpoints ==============

@app.route('/api/llm/status', methods=['GET'])
def llm_status():
    """Check if LMStudio is running"""
    try:
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        return jsonify({'connected': response.status_code == 200})
    except:
        return jsonify({'connected': False})


@app.route('/api/llm/process-note', methods=['POST'])
def process_note():
    """Process a natural language note and extract garden actions"""
    data = request.json
    note_text = data.get('note', '')
    
    if not note_text:
        return jsonify({'error': 'No note provided'}), 400
    
    try:
        system_prompt = """You are a helpful garden assistant that extracts ALL garden data from user notes.

CRITICAL INSTRUCTIONS:
1. Extract EVERY plant mentioned, even if multiple plants are in a single sentence
2. When a plant has a variety (e.g., "Mint (Spearmint)" or "Lettuce - Buttercrunch"), include the variety in parentheses
3. If a note mentions multiple varieties of the same plant, create SEPARATE actions for each variety
4. Always add plants that don't exist yet before logging growth/watering for them
5. Extract growth observations as log_growth (health_rating 1-10, notes about vigor/condition)
6. Create tasks for any mentioned future actions or maintenance needs
7. Use update_plant_status when plants are "pulled", "removed", "harvested completely", or "finished"

EXAMPLES:
- "Spearmint sending aggressive runners" = add_plant(Mint (Spearmint)) + log_growth with notes
- "Chocolate Mint more contained" = add_plant(Mint (Chocolate Mint)) + log_growth with notes  
- "Second succession Red Oak Leaf at 2-week stage" = add_plant(Lettuce (Red Oak Leaf)) with notes
- "Trimmed back 40%" = log_growth with notes + possibly create_task for future trimming

Be thorough! Extract ALL plants and ALL observations. Today's date is """ + datetime.now().strftime('%Y-%m-%d')
        
        response = requests.post(
            LMSTUDIO_URL,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": note_text}
                ],
                "tools": GARDEN_TOOLS,
                "tool_choice": "auto",
                "temperature": 0.1
            },
            timeout=60
        )
        
        if response.status_code != 200:
            return jsonify({'error': 'LLM request failed', 'details': response.text}), 500
        
        result = response.json()
        message = result.get('choices', [{}])[0].get('message', {})
        tool_calls = message.get('tool_calls', [])
        
        extracted_actions = []
        for call in tool_calls:
            func = call.get('function', {})
            action = {
                'action': func.get('name'),
                'parameters': json.loads(func.get('arguments', '{}'))
            }
            extracted_actions.append(action)
        
        # Save the note
        note_record = create_note({
            'raw_text': note_text,
            'processed': len(extracted_actions) > 0,
            'extracted_data': extracted_actions
        })
        
        return jsonify({
            'success': True,
            'extracted_actions': extracted_actions,
            'note_id': note_record.get('id') if note_record else None
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'LLM request timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/llm/apply-actions', methods=['POST'])
def apply_actions():
    """Apply extracted actions to the database"""
    data = request.json
    actions = data.get('actions', [])
    results = []
    
    for action in actions:
        action_name = action.get('action')
        params = action.get('parameters', {})
        
        try:
            if action_name == 'add_plant':
                quantity = params.get('quantity', 1)
                if quantity > 1:
                    # Batch create
                    plants_created = []
                    for i in range(quantity):
                        instance_num = get_next_instance_number(params.get('name'), params.get('variety'))
                        plant_data = {**params, 'instance_number': instance_num}
                        plant = create_plant(plant_data)
                        if plant:
                            plants_created.append(plant)
                    results.append({'action': action_name, 'success': True, 'count': len(plants_created)})
                else:
                    instance_num = get_next_instance_number(params.get('name'), params.get('variety'))
                    plant_data = {**params, 'instance_number': instance_num}
                    plant = create_plant(plant_data)
                    results.append({'action': action_name, 'success': plant is not None})
                
            elif action_name == 'log_watering':
                plant = find_plant_by_name(params.get('plant_name', ''))
                if plant:
                    log = create_watering(plant['id'], params)
                    results.append({'action': action_name, 'success': log is not None})
                else:
                    results.append({'action': action_name, 'success': False, 'error': 'Plant not found'})
                
            elif action_name == 'log_fertilization':
                plant = find_plant_by_name(params.get('plant_name', ''))
                if plant:
                    log = create_fertilization(plant['id'], params)
                    results.append({'action': action_name, 'success': log is not None})
                else:
                    results.append({'action': action_name, 'success': False, 'error': 'Plant not found'})
                
            elif action_name == 'log_harvest':
                plant = find_plant_by_name(params.get('plant_name', ''))
                if plant:
                    log = create_harvest(plant['id'], params)
                    results.append({'action': action_name, 'success': log is not None})
                else:
                    results.append({'action': action_name, 'success': False, 'error': 'Plant not found'})
                
            elif action_name == 'log_growth':
                plant = find_plant_by_name(params.get('plant_name', ''))
                if plant:
                    log = create_growth_log(plant['id'], params)
                    results.append({'action': action_name, 'success': log is not None})
                else:
                    results.append({'action': action_name, 'success': False, 'error': 'Plant not found'})
                
            elif action_name == 'report_pest_issue':
                plant = find_plant_by_name(params.get('plant_name', ''))
                if plant:
                    issue = create_pest_issue(plant['id'], params)
                    results.append({'action': action_name, 'success': issue is not None})
                else:
                    results.append({'action': action_name, 'success': False, 'error': 'Plant not found'})
                
            elif action_name == 'create_task':
                task = create_task(params)
                results.append({'action': action_name, 'success': task is not None})
                
            elif action_name == 'log_weather':
                log = create_weather_log(params)
                results.append({'action': action_name, 'success': log is not None})
                
            elif action_name == 'update_plant_status':
                plant = find_plant_by_name(params.get('plant_name', ''))
                if plant:
                    updated = update_plant(plant['id'], {'status': params.get('status')})
                    results.append({'action': action_name, 'success': updated is not None})
                else:
                    results.append({'action': action_name, 'success': False, 'error': 'Plant not found'})
                    
            elif action_name == 'add_budget_item':
                product = create_product(params)
                results.append({'action': action_name, 'success': product is not None})
                
            else:
                results.append({'action': action_name, 'success': False, 'error': 'Unknown action'})
                
        except Exception as e:
            results.append({'action': action_name, 'success': False, 'error': str(e)})
    
    return jsonify({'results': results})


# ============== Plant Endpoints ==============

@app.route('/api/plants', methods=['GET'])
def get_plants():
    """Get all plants"""
    status = request.args.get('status')
    plants = list_plants(status)
    return jsonify(plants)


@app.route('/api/plants', methods=['POST'])
def add_plant():
    """Add a new plant (supports batch creation with quantity)"""
    data = request.json
    quantity = data.get('quantity', 1)
    
    plants_created = []
    for i in range(quantity):
        instance_num = get_next_instance_number(data.get('name'), data.get('variety'))
        plant_data = {**data, 'instance_number': instance_num}
        plant = create_plant(plant_data)
        if plant:
            plants_created.append(plant)
    
    if quantity > 1:
        return jsonify(plants_created), 201
    elif plants_created:
        return jsonify(plants_created[0]), 201
    else:
        return jsonify({'error': 'Failed to create plant'}), 500


@app.route('/api/plants/<plant_id>', methods=['GET'])
def get_plant_by_id(plant_id):
    """Get a plant by ID"""
    plant = get_plant(plant_id)
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    return jsonify(plant)


@app.route('/api/plants/<plant_id>', methods=['PUT'])
def update_plant_by_id(plant_id):
    """Update a plant"""
    data = request.json
    plant = update_plant(plant_id, data)
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    return jsonify(plant)


@app.route('/api/plants/<plant_id>', methods=['DELETE'])
def delete_plant_by_id(plant_id):
    """Delete a plant"""
    if delete_plant(plant_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Plant not found'}), 404


@app.route('/api/plants/by-code/<code>', methods=['GET'])
def get_plant_by_code_endpoint(code):
    """Look up a plant by its unique QR code"""
    plant = get_plant_by_code(code)
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    return jsonify(plant)


@app.route('/plant/<code>')
def plant_qr_redirect(code):
    """Redirect from QR code scan to the dashboard with plant selected."""
    plant = get_plant_by_code(code)
    if not plant:
        return redirect('/?error=plant_not_found')
    return redirect(f'/?plant={plant["id"]}&action=view')


# ============== QR/Label Endpoints ==============

@app.route('/api/plants/<plant_id>/qr', methods=['GET'])
def get_plant_qr(plant_id):
    """Generate QR code for a plant"""
    plant = get_plant(plant_id)
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    
    qr_url = f"{request.host_url}plant/{plant['unique_code']}"
    
    qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_L, box_size=10, border=2)
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png')


@app.route('/api/plants/<plant_id>/label', methods=['GET'])
def get_plant_label(plant_id):
    """Generate a printable label image for 12x40mm stickers (at 300 DPI)"""
    from PIL import Image, ImageDraw, ImageFont
    
    plant = get_plant(plant_id)
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    
    label_width = 450
    label_height = 130
    
    label = Image.new('RGB', (label_width, label_height), 'white')
    draw = ImageDraw.Draw(label)
    
    qr_url = f"{request.host_url}plant/{plant['unique_code']}"
    
    qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_L, box_size=4, border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_size = label_height - 10
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)
    label.paste(qr_img, (5, 5))
    
    text_x = qr_size + 15
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 28)
        font_medium = ImageFont.truetype("arial.ttf", 18)
        font_small = ImageFont.truetype("arial.ttf", 14)
    except:
        try:
            font_large = ImageFont.truetype("DejaVuSans.ttf", 28)
            font_medium = ImageFont.truetype("DejaVuSans.ttf", 18)
            font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large
    
    display_name = plant.get('display_name', plant.get('name', ''))
    if len(display_name) > 15:
        display_name = display_name[:14] + "…"
    
    draw.text((text_x, 10), display_name, fill='black', font=font_large)
    
    if plant.get('variety'):
        variety_text = plant['variety'][:20] + "…" if len(plant['variety']) > 20 else plant['variety']
        draw.text((text_x, 45), variety_text, fill='gray', font=font_medium)
    
    draw.text((text_x, 75), plant.get('unique_code', ''), fill='black', font=font_medium)
    
    if plant.get('location'):
        loc_text = plant['location'][:18] + "…" if len(plant['location']) > 18 else plant['location']
        draw.text((text_x, 100), f"📍 {loc_text}", fill='gray', font=font_small)
    
    img_buffer = io.BytesIO()
    label.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png')


# ============== Plant Image Upload ==============

@app.route('/api/plant/<plant_id>/image', methods=['POST'])
def upload_plant_image(plant_id):
    """Upload an image for a plant"""
    plant = get_plant(plant_id)
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    
    data = request.json
    image_data = data.get('image_data')
    
    if not image_data:
        return jsonify({'error': 'No image data provided'}), 400
    
    try:
        # Create images directory if it doesn't exist
        images_dir = os.path.join(get_storage_path(), 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        # Decode base64 image
        # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # Generate filename using plant ID and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{plant_id}_{timestamp}.jpg"
        filepath = os.path.join(images_dir, filename)
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        # Update plant metadata with image URL
        image_url = f"/images/{filename}"
        update_plant(plant_id, {'image_url': image_url})
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'image_url': image_url
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to upload image: {str(e)}'}), 500


@app.route('/images/<filename>')
def serve_plant_image(filename):
    """Serve plant images from the images directory"""
    images_dir = os.path.join(get_storage_path(), 'images')
    return send_from_directory(images_dir, filename)


# ============== Growth Log Endpoints ==============

@app.route('/api/plants/<plant_id>/growth', methods=['GET'])
def get_growth_logs_endpoint(plant_id):
    """Get growth logs for a plant"""
    logs = get_growth_logs(plant_id)
    return jsonify(logs)


@app.route('/api/plants/<plant_id>/growth', methods=['POST'])
def add_growth_log(plant_id):
    """Add a growth log for a plant"""
    data = request.json
    log = create_growth_log(plant_id, data)
    if log:
        return jsonify(log), 201
    return jsonify({'error': 'Failed to create growth log'}), 500


# ============== Watering Endpoints ==============

@app.route('/api/plants/<plant_id>/watering', methods=['GET'])
def get_waterings_endpoint(plant_id):
    """Get watering logs for a plant"""
    logs = get_waterings(plant_id)
    return jsonify(logs)


@app.route('/api/plants/<plant_id>/watering', methods=['POST'])
def add_watering(plant_id):
    """Add a watering log for a plant"""
    data = request.json
    log = create_watering(plant_id, data)
    if log:
        return jsonify(log), 201
    return jsonify({'error': 'Failed to create watering log'}), 500


@app.route('/api/waterings', methods=['GET'])
def get_all_waterings_endpoint():
    """Get all watering logs"""
    logs = get_all_waterings()
    return jsonify(logs)


# ============== Fertilization Endpoints ==============

@app.route('/api/plants/<plant_id>/fertilization', methods=['GET'])
def get_fertilizations_endpoint(plant_id):
    """Get fertilization logs for a plant"""
    logs = get_fertilizations(plant_id)
    return jsonify(logs)


@app.route('/api/plants/<plant_id>/fertilization', methods=['POST'])
def add_fertilization(plant_id):
    """Add a fertilization log for a plant"""
    data = request.json
    log = create_fertilization(plant_id, data)
    if log:
        return jsonify(log), 201
    return jsonify({'error': 'Failed to create fertilization log'}), 500


# ============== Harvest Endpoints ==============

@app.route('/api/harvests', methods=['GET'])
def get_harvests_endpoint():
    """Get all harvests"""
    harvests = get_harvests()
    return jsonify(harvests)


@app.route('/api/plants/<plant_id>/harvest', methods=['POST'])
def add_harvest(plant_id):
    """Add a harvest log for a plant"""
    data = request.json
    log = create_harvest(plant_id, data)
    if log:
        return jsonify(log), 201
    return jsonify({'error': 'Failed to create harvest log'}), 500


# ============== Pest Endpoints ==============

@app.route('/api/plants/<plant_id>/pest', methods=['GET'])
def get_pests_endpoint(plant_id):
    """Get pest issues for a plant"""
    issues = get_pest_issues(plant_id)
    return jsonify(issues)


@app.route('/api/plants/<plant_id>/pest', methods=['POST'])
def add_pest_issue(plant_id):
    """Add a pest issue for a plant"""
    data = request.json
    issue = create_pest_issue(plant_id, data)
    if issue:
        return jsonify(issue), 201
    return jsonify({'error': 'Failed to create pest issue'}), 500


@app.route('/api/pests/active', methods=['GET'])
def get_active_pests():
    """Get all active pest issues"""
    issues = get_pest_issues(active_only=True)
    return jsonify(issues)


# ============== Task Endpoints ==============

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    completed = request.args.get('completed')
    if completed is not None:
        completed = completed.lower() == 'true'
    tasks = list_tasks(completed)
    return jsonify(tasks)


@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Create a new task"""
    data = request.json
    task = create_task(data)
    if task:
        return jsonify(task), 201
    return jsonify({'error': 'Failed to create task'}), 500


@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_endpoint(task_id):
    """Get a task by ID"""
    task = get_task(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task)


@app.route('/api/tasks/<task_id>/complete', methods=['PUT'])
def complete_task_endpoint(task_id):
    """Mark a task as complete"""
    task = complete_task(task_id)
    if task:
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task_endpoint(task_id):
    """Delete a task"""
    if delete_task(task_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Task not found'}), 404


# ============== Weather Endpoints ==============

@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Get all weather logs"""
    logs = list_weather_logs()
    return jsonify(logs)


@app.route('/api/weather', methods=['POST'])
def add_weather():
    """Add a weather log"""
    data = request.json
    log = create_weather_log(data)
    if log:
        return jsonify(log), 201
    return jsonify({'error': 'Failed to create weather log'}), 500


# ============== Notes Endpoints ==============

@app.route('/api/notes', methods=['GET'])
def get_notes():
    """Get all notes"""
    notes = list_notes()
    return jsonify(notes)


@app.route('/api/notes', methods=['POST'])
def add_note():
    """Add a note"""
    data = request.json
    note = create_note(data)
    if note:
        return jsonify(note), 201
    return jsonify({'error': 'Failed to create note'}), 500


# ============== Recipe Endpoints ==============

@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    """Get all recipes"""
    recipe_type = request.args.get('type')
    recipes = list_recipes(recipe_type)
    return jsonify(recipes)


@app.route('/api/recipes', methods=['POST'])
def add_recipe():
    """Create a new recipe"""
    data = request.json
    recipe = create_recipe(data)
    if recipe:
        return jsonify(recipe), 201
    return jsonify({'error': 'Failed to create recipe'}), 500


@app.route('/api/recipes/<recipe_id>', methods=['GET'])
def get_recipe_endpoint(recipe_id):
    """Get a recipe by ID"""
    recipe = get_recipe(recipe_id)
    if not recipe:
        return jsonify({'error': 'Recipe not found'}), 404
    return jsonify(recipe)


@app.route('/api/recipes/<recipe_id>', methods=['PUT'])
def update_recipe_endpoint(recipe_id):
    """Update a recipe"""
    data = request.json
    recipe = update_recipe(recipe_id, data)
    if recipe:
        return jsonify(recipe)
    return jsonify({'error': 'Recipe not found'}), 404


@app.route('/api/recipes/<recipe_id>', methods=['DELETE'])
def delete_recipe_endpoint(recipe_id):
    """Delete a recipe"""
    if delete_recipe(recipe_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Recipe not found'}), 404


# ============== Budget Endpoints ==============

@app.route('/api/budget/products', methods=['GET'])
def get_products():
    """Get all budget products"""
    category = request.args.get('category')
    products = list_products(category)
    return jsonify(products)


@app.route('/api/budget/products', methods=['POST'])
def add_product():
    """Add a new product"""
    data = request.json
    product = create_product(data)
    if product:
        return jsonify(product), 201
    return jsonify({'error': 'Failed to create product'}), 500


@app.route('/api/budget/products/<product_id>', methods=['GET'])
def get_product_endpoint(product_id):
    """Get a product by ID"""
    product = get_product(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify(product)


@app.route('/api/budget/products/<product_id>', methods=['PUT'])
def update_product_endpoint(product_id):
    """Update a product"""
    data = request.json
    product = update_product(product_id, data)
    if product:
        return jsonify(product)
    return jsonify({'error': 'Product not found'}), 404


@app.route('/api/budget/products/<product_id>', methods=['DELETE'])
def delete_product_endpoint(product_id):
    """Delete a product"""
    if delete_product(product_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Product not found'}), 404


@app.route('/api/budget/summary', methods=['GET'])
def get_budget_summary_endpoint():
    """Get budget summary"""
    summary = get_budget_summary()
    return jsonify(summary)


@app.route('/api/budget/cost-per-plant/<plant_id>', methods=['GET'])
def get_cost_per_plant_endpoint(plant_id):
    """Get cost analysis for a specific plant"""
    cost = get_cost_per_plant(plant_id)
    return jsonify(cost)


# ============== Chart Data Endpoints ==============

@app.route('/api/charts/growth/<plant_id>', methods=['GET'])
def get_growth_chart(plant_id):
    """Get growth data formatted for charts"""
    data = get_growth_chart_data(plant_id)
    return jsonify(data)


@app.route('/api/charts/watering', methods=['GET'])
@app.route('/api/charts/watering/<plant_id>', methods=['GET'])
def get_watering_chart(plant_id=None):
    """Get watering data for all plants or specific plant, formatted for charts"""
    if not plant_id:
        plant_id = request.args.get('plant_id')
    data = get_watering_chart_data(plant_id)
    return jsonify(data)


@app.route('/api/charts/budget', methods=['GET'])
def get_budget_chart():
    """Get budget data formatted for charts"""
    data = get_budget_chart_data()
    return jsonify(data)


# ============== Dashboard Endpoints ==============

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days = now + timedelta(days=7)
    
    plants = list_plants()
    active_plants = len([p for p in plants if p.get('status') == 'active'])
    
    tasks = list_tasks(completed=False)
    pending_tasks = len(tasks)
    
    harvests = get_harvests()
    recent_harvests = len([h for h in harvests 
                          if h.get('date') and h.get('date') >= thirty_days_ago.isoformat()[:10]])
    
    pests = get_pest_issues(active_only=True)
    active_pests = len(pests)
    
    return jsonify({
        'active_plants': active_plants,
        'pending_tasks': pending_tasks,
        'recent_harvests': recent_harvests,
        'active_pests': active_pests
    })


# ============== Data Management ==============

@app.route('/api/storage/path', methods=['GET'])
def get_storage_path_endpoint():
    """Get the current MD storage path"""
    return jsonify({'path': str(get_storage_path())})


@app.route('/api/storage/path', methods=['PUT'])
def set_storage_path():
    """Set a new MD storage path (for Obsidian vault integration)"""
    data = request.json
    new_path = data.get('path')
    if new_path:
        os.environ['GARDEN_MD_PATH'] = new_path
        ensure_directories()
        return jsonify({'success': True, 'path': new_path})
    return jsonify({'error': 'No path provided'}), 400


# ============== Main ==============

if __name__ == '__main__':
    print("Initializing MD storage...")
    ensure_directories()
    print(f"Storage path: {get_storage_path()}")
    app.run(debug=True)
