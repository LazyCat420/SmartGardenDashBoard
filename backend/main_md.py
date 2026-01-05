"""
Smart Garden Dashboard - Main API Server
Using Markdown files for Obsidian-compatible storage
"""

from flask import Flask, request, jsonify, send_file, redirect, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Dict
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
    create_note, list_notes, update_note, delete_note,
    # Recipes
    create_recipe, get_recipe, list_recipes, update_recipe, delete_recipe,
    find_recipe_by_name,
    # Budget
    create_product, get_product, list_products, update_product, delete_product,
    get_budget_summary, get_cost_per_plant,
    find_product_by_name,
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
            "description": "Log a watering event for a plant. If the user mentions using a compost tea or nutrient recipe (like 'veg compost tea', 'flower tea', etc.), extract the recipe name. The system will automatically match it to saved recipes and calculate ingredient costs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "amount_ml": {"type": "number", "description": "Amount in ml"},
                    "amount_value": {"type": "number", "description": "Amount in other units"},
                    "amount_unit": {"type": "string", "description": "Unit (ml, gallons, cups)"},
                    "method": {"type": "string", "description": "Watering method - use specific recipe name if a tea/recipe was mentioned (e.g., 'veg compost tea', 'flower compost tea'), otherwise use general method (watering can, hose, spray, soak)"},
                    "recipe_name": {"type": "string", "description": "Name of compost tea or nutrient recipe used if mentioned (e.g., 'veg compost tea', 'bloom tea', 'kelp tea'). System will fuzzy-match to saved recipes and auto-fill ingredients/costs."},
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


# ============== LLM Settings Helpers ==============
LLM_SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')

def load_llm_settings() -> Dict[str, str]:
    """Load LLM settings from file or return defaults."""
    defaults = { 'url': LMSTUDIO_URL, 'model': MODEL_NAME }
    try:
        if os.path.exists(LLM_SETTINGS_FILE):
            with open(LLM_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return { 'url': settings.get('url', LMSTUDIO_URL), 'model': settings.get('model', MODEL_NAME) }
    except Exception as e:
        print('Failed to load LLM settings:', e)
    return defaults

def save_llm_settings(url: str, model: str) -> bool:
    try:
        settings = { 'url': url, 'model': model }
        with open(LLM_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        # Update module-level vars
        global LMSTUDIO_URL, MODEL_NAME
        LMSTUDIO_URL = url
        MODEL_NAME = model
        return True
    except Exception as e:
        return False

# Initialize settings from file on startup
try:
    _startup_settings = load_llm_settings()
    LMSTUDIO_URL = _startup_settings.get('url', LMSTUDIO_URL)
    MODEL_NAME = _startup_settings.get('model', MODEL_NAME)
    print(f"Startup: Loaded LLM settings - URL: {LMSTUDIO_URL}, Model: {MODEL_NAME}")
except Exception as e:
    print(f"Startup: Failed to load LLM settings: {e}")


# ============== Static Files ==============

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')


# ============== LLM Endpoints ==============

@app.route('/api/llm/status', methods=['GET'])
def llm_status():
    """Check if LMStudio is running"""
    try:
        settings = load_llm_settings()
        # Probe models endpoint to determine connectivity
        base_url = settings.get('url') or LMSTUDIO_URL
        models_url = base_url.replace('/chat/completions', '/models') if '/chat/completions' in base_url else base_url.rstrip('/') + '/models'
        resp = requests.get(models_url, timeout=2)
        connected = resp.status_code == 200
        return jsonify({'connected': connected, 'url': settings.get('url'), 'model': settings.get('model')})
    except Exception:
        settings = load_llm_settings()
        return jsonify({'connected': False, 'url': settings.get('url'), 'model': settings.get('model')})


@app.route('/api/llm/models', methods=['GET'])
def llm_models():
    """Return a list of models available from LMStudio/proxy"""
    try:
        # Load settings to allow custom LMStudio URL
        settings = load_llm_settings()
        base_url = settings.get('url') or LMSTUDIO_URL
        # Models endpoint is typically /v1/models (OpenAI-compatible)
        models_url = base_url.replace('/chat/completions', '/models') if '/chat/completions' in base_url else base_url.rstrip('/') + '/models'
        resp = requests.get(models_url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            # OpenAI-compatible format: { "object": "list", "data": [{"id": "model-name", ...}] }
            if isinstance(data, dict) and 'data' in data:
                # Standard OpenAI/LMStudio format
                model_names = [m.get('id') for m in data.get('data', []) if m.get('id')]
                return jsonify({'models': model_names})
            elif isinstance(data, dict):
                # Fallback: dict with model names as keys
                model_names = list(data.keys())
                return jsonify({'models': model_names})
            elif isinstance(data, list):
                # List of model objects or strings
                model_names = []
                for item in data:
                    if isinstance(item, dict) and 'id' in item:
                        model_names.append(item['id'])
                    elif isinstance(item, str):
                        model_names.append(item)
                return jsonify({'models': model_names})
            return jsonify({'models': []})
        else:
            return jsonify({'error': 'Failed to fetch models', 'code': resp.status_code}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/llm/process-note', methods=['POST'])
def process_note():
    """Process a natural language note and extract garden actions"""
    data = request.json
    note_text = data.get('note', '')
    
    if not note_text:
        return jsonify({'error': 'No note provided'}), 400
    
    try:
        # Get list of existing recipes for context
        recipes = list_recipes()
        recipe_names = [r.get('name', '') for r in recipes] if recipes else []
        recipe_list = ", ".join(recipe_names) if recipe_names else "No recipes saved yet"
        
        system_prompt = f"""You are a helpful garden assistant that extracts ALL garden data from user notes.

CRITICAL INSTRUCTIONS FOR CATEGORIZING ACTIONS:
1. Extract EVERY piece of information from the note into the appropriate action type:
   - WATERING: Any mention of watering, using tea/recipe, irrigating. Use log_watering.
   - GROWTH: Any mention of height, size, health, appearance, looking sick/good. Use log_growth.
   - HARVEST: Any mention of picking, harvesting, collecting produce. Use log_harvest.
   - ISSUES/PESTS: Any mention of pests, disease, problems, wilting, overwatering damage. Use report_pest_issue.
   - STATUS UPDATES: Plant died, removed, finished. Use update_plant_status.

2. RECIPE MATCHING: When user mentions using a tea or recipe for watering:
   - Extract the recipe name exactly as mentioned (e.g., "veg compost tea", "flower tea", "bloom tea")
   - Put the recipe name in BOTH the 'method' and 'recipe_name' fields
   - Available recipes in the system: {recipe_list}
   - The system will automatically fuzzy-match to the closest recipe and calculate costs

3. SPLIT MULTIPLE OBSERVATIONS: A single sentence may contain MULTIPLE pieces of info:
   - "Water with veg compost tea. Plant is 12 inches tall now. Looks sick will stop overwatering."
   = log_watering (recipe_name: "veg compost tea") 
   + log_growth (height_cm: 30.48, notes: "12 inches tall")
   + report_pest_issue (pest_type: "overwatering damage", severity: "moderate", notes: "looks sick, will stop overwatering")

4. HEALTH DESCRIPTIONS map to health_rating (1-10):
   - "looking great/thriving/healthy" = 8-10
   - "doing okay/normal" = 5-7  
   - "not doing well/struggling" = 3-5
   - "looks sick/wilting/dying" = 1-3

5. Convert measurements: inches to cm (multiply by 2.54), feet to cm (multiply by 30.48)

6. When a plant has a variety (e.g., "Mint (Spearmint)"), include the variety in parentheses

Today's date is """ + datetime.now().strftime('%Y-%m-%d')
        
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


@app.route('/api/llm/settings', methods=['GET'])
def get_llm_settings():
    settings = load_llm_settings()
    return jsonify({
        'url': settings.get('url', LMSTUDIO_URL),
        'model': settings.get('model', MODEL_NAME),
        'defaults': {'url': LMSTUDIO_URL, 'model': MODEL_NAME}
    })


@app.route('/api/llm/settings', methods=['POST'])
def update_llm_settings():
    data = request.json or {}
    url = data.get('url', LMSTUDIO_URL)
    model = data.get('model', MODEL_NAME)
    if save_llm_settings(url, model):
        return jsonify({'success': True, 'url': url, 'model': model})
    return jsonify({'success': False, 'message': 'Failed to save settings'}), 500


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
                    # Auto-fill recipe data if recipe_name is provided
                    recipe_name = params.get('recipe_name') or params.get('method', '')
                    if recipe_name:
                        # Try to find matching recipe using fuzzy matching
                        recipe = find_recipe_by_name(recipe_name)
                        if recipe:
                            # Auto-fill recipe data
                            params['recipe_id'] = recipe.get('id')
                            params['recipe_name'] = recipe.get('name')
                            params['ingredients'] = recipe.get('ingredients', [])
                            params['total_cost'] = recipe.get('total_cost', 0)
                            # Set method to recipe name if not already specific
                            if not params.get('method') or params.get('method') == recipe_name:
                                params['method'] = recipe.get('name')
                    
                    log = create_watering(plant['id'], params)
                    results.append({'action': action_name, 'success': log is not None, 
                                   'recipe_matched': params.get('recipe_name') if recipe_name else None})
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


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard data similar to SQL backend for MD-based storage"""
    metric = request.args.get('metric', 'growth_rate')
    category = request.args.get('category', 'all')
    plant_ids = request.args.get('plant_ids', '')

    # Get plants (MD storage format)
    if category == 'all':
        plants_list = list_plants('active')
    else:
        plants_list = [p for p in list_plants('active') if p.get('name', '').lower() == category.lower()]

    # Filter by IDs if provided
    if plant_ids:
        ids = [s.strip() for s in plant_ids.split(',') if s.strip()]
        plants_list = [p for p in plants_list if p.get('id') in ids]

    leaderboard_data = []
    for p in plants_list:
        plant_id = p.get('id')
        growth_logs = get_growth_logs(plant_id) or []
        # growth_logs are sorted desc in md_service -> we want ascending by date
        growth_sorted = sorted(growth_logs, key=lambda x: x.get('date', ''))
        health_values = [g.get('health_rating') for g in growth_sorted if g.get('health_rating') is not None]

        # Growth rate calculation
        if len(growth_sorted) >= 2:
            try:
                first = growth_sorted[0]
                last = growth_sorted[-1]
                first_date = datetime.fromisoformat(first.get('date'))
                last_date = datetime.fromisoformat(last.get('date'))
                days = (last_date - first_date).days or 1
                height_diff = (last.get('height_cm') or 0) - (first.get('height_cm') or 0)
                growth_rate = round(height_diff / days, 3) if days > 0 else 0
            except Exception:
                growth_rate = 0
        else:
            growth_rate = 0

        # Average health
        health = round(sum(health_values) / len(health_values), 1) if health_values else 0

        # Harvests count
        harvests = get_harvests(plant_id) or []
        harvest_count = len(harvests)

        latest_height = 0
        if growth_sorted:
            latest_height = growth_sorted[-1].get('height_cm') or 0

        leaderboard_data.append({
            'id': plant_id,
            'name': p.get('name'),
            'display_name': p.get('display_name', p.get('name')),
            'variety': p.get('variety'),
            'category': p.get('name', '').lower(),
            'growth_rate': growth_rate,
            'health': health,
            'harvests': harvest_count,
            'latest_height': latest_height
        })

    # Sort by metric
    leaderboard_data.sort(key=lambda x: x.get(metric, 0), reverse=True)
    # Assign rank
    for i, item in enumerate(leaderboard_data):
        item['rank'] = i + 1

    # Categories (unique names)
    categories = sorted(list(set([p.get('name', '').lower() for p in list_plants('active')])))

    return jsonify({'rankings': leaderboard_data, 'leaderboard': leaderboard_data, 'metric': metric, 'categories': categories})


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


@app.route('/api/weather/search', methods=['GET'])
def search_weather():
    """
    Search for current weather using wttr.in
    Query params: q (city name or zipcode)
    """
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (SmartGardenDashboard/1.0)'
        }
        
        response = requests.get(f"https://wttr.in/{query}?format=j1", headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Transform wttr.in data to expected frontend format
            try:
                current = data['current_condition'][0]
                area = data['nearest_area'][0]
                forecast = data['weather'][0]
                
                result = {
                    'location': area['areaName'][0]['value'],
                    'country': area['country'][0]['value'],
                    'conditions': current['weatherDesc'][0]['value'],
                    'temperature': float(current['temp_C']),
                    'temperature_F': float(current['temp_F']),
                    'temperature_high': float(forecast['maxtempC']),
                    'temperature_high_F': float(forecast['maxtempF']),
                    'temperature_low': float(forecast['mintempC']),
                    'temperature_low_F': float(forecast['mintempF']),
                    'humidity': int(current['humidity']),
                    'wind_speed': current['windspeedKmph'], # Keep as string or float, frontend expects string/number
                    'icon': '' # wttr.in doesn't provide openweathermap icons easily, leave empty or map if needed
                }
                return jsonify(result)
            except (KeyError, IndexError, ValueError) as e:
                print(f"Error parsing weather data: {e}")
                return jsonify({'error': 'Failed to parse weather data'}), 502
                
        elif response.status_code == 404:
            return jsonify({'error': 'Location not found'}), 404
        else:
            return jsonify({'error': f'Weather provider returned {response.status_code}'}), 502
            
    except requests.RequestException as e:
        print(f"Weather search error: {e}")
        return jsonify({'error': 'Failed to contact weather provider'}), 503
    except Exception as e:
        print(f"Unexpected weather error: {e}")
        return jsonify({'error': 'Internal server error processing weather'}), 500


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


@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note_endpoint(note_id):
    """Delete a note"""
    if delete_note(note_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Note not found'}), 404


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
    """Update a product and optionally recalculate recipe costs"""
    data = request.json
    product = update_product(product_id, data)
    if product:
        # Auto-recalculate recipe costs if price changed
        if 'price' in data or 'purchase_price' in data or 'size_amount' in data:
            # Find recipes that use this product and recalculate their costs
            recipes = list_recipes()
            for recipe in recipes:
                ingredients = recipe.get('ingredients', [])
                for ing in ingredients:
                    if ing.get('product_id') == product_id or \
                       (ing.get('product_name', '').lower() == product.get('name', '').lower()):
                        # This recipe uses this product, recalculate
                        update_recipe(recipe['id'], {'ingredients': ingredients})
                        break
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


@app.route('/api/budget/recalculate-recipe-costs', methods=['POST'])
def recalculate_recipe_costs():
    """
    Recalculate costs for all recipes based on current product prices.
    Call this after updating product prices to keep recipes in sync.
    """
    recipes = list_recipes()
    updated_count = 0
    
    for recipe in recipes:
        # Trigger cost recalculation by updating with same ingredients
        updated = update_recipe(recipe['id'], {'ingredients': recipe.get('ingredients', [])})
        if updated:
            updated_count += 1
    
    return jsonify({
        'success': True,
        'recipes_updated': updated_count,
        'message': f'Recalculated costs for {updated_count} recipes'
    })


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

def get_local_ip():
    """Get the local IP address for network access"""
    import socket
    try:
        # Connect to an external address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


if __name__ == '__main__':
    import argparse
    import ssl
    
    parser = argparse.ArgumentParser(description='Smart Garden Dashboard Server')
    parser.add_argument('--https', action='store_true', help='Enable HTTPS')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on (default: 5000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to (default: 0.0.0.0 for network access)')
    args = parser.parse_args()
    
    print("Initializing MD storage...")
    ensure_directories()
    print(f"Storage path: {get_storage_path()}")
    
    local_ip = get_local_ip()
    
    if args.https:
        # Generate or use existing SSL certificates
        cert_dir = os.path.dirname(os.path.abspath(__file__))
        cert_file = os.path.join(cert_dir, 'cert.pem')
        key_file = os.path.join(cert_dir, 'key.pem')
        
        # Check if certificates exist, if not generate them
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            print("SSL certificates not found. Generating...")
            from generate_ssl import generate_ssl_certificates
            cert_file, key_file = generate_ssl_certificates()
        
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        
        print(f"\n{'='*60}")
        print(f"🌱 Smart Garden Dashboard - HTTPS Server")
        print(f"{'='*60}")
        print(f"  Local:   https://localhost:{args.port}")
        print(f"  Network: https://{local_ip}:{args.port}")
        print(f"{'='*60}")
        print(f"⚠️  Note: You'll need to accept the self-signed certificate")
        print(f"    in your browser on first visit.")
        print(f"{'='*60}\n")
        
        app.run(
            host=args.host,
            port=args.port,
            debug=True,
            ssl_context=context
        )
    else:
        print(f"\n{'='*60}")
        print(f"🌱 Smart Garden Dashboard - HTTP Server")
        print(f"{'='*60}")
        print(f"  Local:   http://localhost:{args.port}")
        print(f"  Network: http://{local_ip}:{args.port}")
        print(f"{'='*60}")
        print(f"  Tip: Use --https flag for secure connections")
        print(f"{'='*60}\n")
        
        app.run(
            host=args.host,
            port=args.port,
            debug=True
        )

