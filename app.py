from flask import Flask, jsonify, request
from flask_cors import CORS
import database
import sqlite3
import json
import uuid
import llm_service_tools

app = Flask(__name__)
CORS(app)

# Initialize DB on start
database.init_db()

def get_db_connection():
    return database.get_db_connection()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

# --- Plants API ---
@app.route('/api/plants', methods=['GET'])
def get_plants():
    conn = get_db_connection()
    plants = conn.execute('SELECT * FROM plants').fetchall()
    conn.close()
    result = []
    for p in plants:
        p_dict = dict(p)
        # Parse JSON fields
        for field in ['heightHistory', 'healthHistory', 'photos', 'feedingRecipes', 'feedingApplications', 'journalEntries']:
            if p_dict.get(field):
                try:
                    p_dict[field] = json.loads(p_dict[field])
                except:
                    p_dict[field] = []
            else:
                p_dict[field] = []
        result.append(p_dict)
    return jsonify(result)

@app.route('/api/plants', methods=['POST'])
def add_plant():
    data = request.json
    if 'id' not in data:
        data['id'] = str(uuid.uuid4())
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO plants (id, name, type, gridId, quadrant, dateAdded, health, 
                                heightHistory, healthHistory, photos, feedingRecipes, 
                                feedingApplications, journalEntries)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['name'], data['type'], data.get('gridId'), data.get('quadrant'), 
            data.get('dateAdded'), data.get('health'),
            json.dumps(data.get('heightHistory', [])),
            json.dumps(data.get('healthHistory', [])),
            json.dumps(data.get('photos', [])),
            json.dumps(data.get('feedingRecipes', [])),
            json.dumps(data.get('feedingApplications', [])),
            json.dumps(data.get('journalEntries', []))
        ))
        conn.commit()
        conn.close()
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plants/<id>', methods=['DELETE', 'PUT'])
def manage_plant(id):
    if request.method == 'DELETE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM plants WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    elif request.method == 'PUT':
        try:
            data = request.json
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update fields
            cursor.execute('''
                UPDATE plants 
                SET name = ?, type = ?, gridId = ?, quadrant = ?, dateAdded = ?, health = ?, 
                    heightHistory = ?, healthHistory = ?, photos = ?, feedingRecipes = ?, 
                    feedingApplications = ?, journalEntries = ?
                WHERE id = ?
            ''', (
                data['name'], data['type'], data.get('gridId'), data.get('quadrant'), 
                data.get('dateAdded'), data.get('health'),
                json.dumps(data.get('heightHistory', [])),
                json.dumps(data.get('healthHistory', [])),
                json.dumps(data.get('photos', [])),
                json.dumps(data.get('feedingRecipes', [])),
                json.dumps(data.get('feedingApplications', [])),
                json.dumps(data.get('journalEntries', [])),
                id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500


# --- Journal API ---
@app.route('/api/journal', methods=['GET'])
def get_journal_entries():
    conn = get_db_connection()
    entries = conn.execute('SELECT * FROM journal_entries ORDER BY date DESC').fetchall()
    conn.close()
    result = []
    for e in entries:
        e_dict = dict(e)
        e_dict['tags'] = json.loads(e_dict['tags']) if e_dict.get('tags') else []
        e_dict['relatedPlantIds'] = json.loads(e_dict['relatedPlantIds']) if e_dict.get('relatedPlantIds') else []
        e_dict['processed_data'] = json.loads(e_dict['processed_data']) if e_dict.get('processed_data') else None
        result.append(e_dict)
    return jsonify(result)


@app.route('/api/journal', methods=['POST'])
def add_journal_entry():
    data = request.json
    if 'id' not in data:
        data['id'] = str(uuid.uuid4())

    process_with_ai = data.get('processWithAI', False)
    processed_data = data.get('processedData', None)

    conn = get_db_connection()
    cursor = conn.cursor()

    related_plant_ids = []
    tags = []

    if process_with_ai and not processed_data:
        llm_result = llm_service_tools.process_journal_entry(data.get('content', ''))
        if llm_result.get('success'):
            # New tool calling returns extracted_data with arrays
            extracted_data = llm_result.get('extracted_data', {})
            
            # Convert to legacy processed_data format for backward compatibility
            processed_data = {
                'plants_mentioned': extracted_data.get('plants_mentioned', []),
                'actions': [],
                'summary': extracted_data.get('summary', '')
            }
            
            # Convert heights to actions
            for h in extracted_data.get('heights', []):
                processed_data['actions'].append({
                    'action_type': 'height_measurement',
                    'plant': h['plant_name'],
                    'height': h['height'],
                    'unit': h['unit'],
                    'details': f"{h.get('position', '')} {h.get('details', '')}".strip()
                })
            
            # Convert feedings to actions
            for f in extracted_data.get('feedings', []):
                details = f['fertilizer_name']
                if f.get('npk_ratio'):
                    details += f" {f['npk_ratio']}"
                if f.get('concentration'):
                    details += f" @ {f['concentration']}"
                if f.get('frequency'):
                    details += f" ({f['frequency']})"
                processed_data['actions'].append({
                    'action_type': 'feeding',
                    'plant': f['plant_name'],
                    'details': details,
                    'date': f.get('date'),
                    'amount': None
                })
            
            # Convert waterings to actions
            for w in extracted_data.get('waterings', []):
                details = ''
                if w.get('amount'):
                    details = f"{w['amount']} {w.get('unit', '')}".strip()
                if w.get('frequency'):
                    details += f" {w['frequency']}"
                processed_data['actions'].append({
                    'action_type': 'watering',
                    'plant': w['plant_name'],
                    'details': details.strip()
                })

            # Convert prunings to actions
            for p in extracted_data.get('prunings', []):
                processed_data['actions'].append({
                    'action_type': 'pruning',
                    'plant': p['plant_name'],
                    'details': f"{p.get('pruning_type', 'pruning')} - {p.get('details', '')}".strip()
                })

            # Convert harvests to actions
            for h in extracted_data.get('harvests', []):
                details = f"{h.get('amount', '')} {h.get('unit', '')}".strip()
                if h.get('quality'):
                    details += f" Quality: {h['quality']}"
                if h.get('details'):
                    details += f" - {h['details']}"
                processed_data['actions'].append({
                    'action_type': 'harvesting',
                    'plant': h['plant_name'],
                    'details': details.strip()
                })

            # Convert environmental changes to actions
            for e in extracted_data.get('environmental_changes', []):
                details = f"{e.get('change_type', 'env change')}: {e.get('action_taken', '')}"
                if e.get('current_value'):
                    details += f" (Current: {e['current_value']}"
                if e.get('target_value'):
                    details += f" Target: {e['target_value']})"
                else:
                    details += ")"
                if e.get('details'):
                    details += f" - {e['details']}"
                processed_data['actions'].append({
                    'action_type': 'environmental_adjustment',
                    'plant': e['plant_name'],
                    'details': details.strip()
                })
            
            # Store observations as general notes
            for o in extracted_data.get('observations', []):
                severity = o.get('severity', 'neutral')
                processed_data['actions'].append({
                    'action_type': 'observation',
                    'plant': o['plant_name'],
                    'details': f"[{o.get('category', 'general')}] {o.get('observation', '')} (Severity: {severity})"
                })

    if processed_data:
        # Normalize client-side parsed structures to expected LLM format if needed
        if 'plants_mentioned' not in processed_data:
            normalized = {
                'plants_mentioned': [],
                'actions': [],
                'summary': processed_data.get('summary') or ''
            }
            # Client uses plantsMentioned (IDs); try to use names from DB if IDs passed
            client_plants = processed_data.get('plantsMentioned') or []
            if client_plants:
                normalized['plants_mentioned'] = client_plants
            # Convert plantHeights
            for ph in processed_data.get('plantHeights', []) or []:
                name = ph.get('name') or ph.get('plant') or ph.get('plantId')
                normalized['actions'].append({
                    'action_type': 'height_measurement',
                    'plant': name,
                    'height': ph.get('height'),
                    'unit': ph.get('unit', 'cm')
                })
            # Convert nutrientsUsed -> feeding actions
            for nut in processed_data.get('nutrientsUsed', []) or []:
                normalized['actions'].append({
                    'action_type': 'feeding',
                    'plant': None,
                    'details': nut,
                    'amount': None
                })
            processed_data = normalized
        # Map plant names to IDs with improved variety matching
        plants_mentioned = processed_data.get('plants_mentioned', [])
        all_plants = cursor.execute('SELECT id, name, type, variety FROM plants').fetchall()
        plant_map = {p['id']: {'name': p['name'], 'type': p['type'], 'variety': p['variety']} for p in all_plants}
        
        def find_plant_match(plant_name):
            """Find best matching plant ID for a given name, considering varieties"""
            pn = plant_name.lower()
            
            # First: Exact match on full name
            for pid, info in plant_map.items():
                if info['name'] and pn == info['name'].lower():
                    return pid
            
            # Second: Check if variety is mentioned in plant_name and matches DB variety
            for pid, info in plant_map.items():
                if info['variety'] and info['variety'].lower() in pn:
                    # Also check if the base type matches
                    if info['type'] and info['type'].lower() in pn:
                        return pid
            
            # Third: Match on type (e.g., "Tomatoes" matches type="Tomato")
            for pid, info in plant_map.items():
                if info['type'] and info['type'].lower() in pn:
                    return pid
            
            # Fourth: Substring match on name
            for pid, info in plant_map.items():
                if info['name'] and pn in info['name'].lower():
                    return pid
                if info['name'] and info['name'].lower() in pn:
                    return pid
            
            return None
        
        # Track newly created plants so we don't duplicate
        created_plants = {}  # plant_name -> pid
        
        def get_matching_plant_ids(plant_name):
            """
            Get ALL matching plant IDs for a given name.
            - "all tomatoes" -> returns all plants with type containing 'tomato'
            - "cherry tomatoes" -> returns only cherry tomato plants
            - "California Wonder Bell Pepper" -> returns that specific plant
            """
            pn = plant_name.lower().strip()
            matching_ids = []
            
            # Check for "all X" pattern
            is_all_pattern = pn.startswith('all ')
            if is_all_pattern:
                type_to_match = pn[4:].strip()  # Remove "all "
                # Match any plant where the type contains this word
                for pid, info in plant_map.items():
                    if info['type'] and type_to_match in info['type'].lower():
                        matching_ids.append(pid)
                    elif info['name'] and type_to_match in info['name'].lower():
                        matching_ids.append(pid)
                return matching_ids
            
            # Try exact match first
            for pid, info in plant_map.items():
                if info['name'] and pn == info['name'].lower():
                    return [pid]
            
            # Try variety + type match
            for pid, info in plant_map.items():
                if info['variety'] and info['type']:
                    combined = f"{info['variety']} {info['type']}".lower()
                    if pn == combined or pn in combined or combined in pn:
                        matching_ids.append(pid)
            
            if matching_ids:
                return matching_ids
            
            # Try type-only match (e.g., "tomatoes" matches all tomato plants)
            for pid, info in plant_map.items():
                if info['type'] and info['type'].lower() in pn:
                    matching_ids.append(pid)
            
            if matching_ids:
                return matching_ids
            
            # Try substring match
            for pid, info in plant_map.items():
                if info['name'] and (pn in info['name'].lower() or info['name'].lower() in pn):
                    matching_ids.append(pid)
            
            return matching_ids
        
        def get_or_create_plant(plant_name):
            """Find existing plant or create a new one"""
            # First try to match existing plant
            matches = get_matching_plant_ids(plant_name)
            if matches:
                return matches[0]  # Return first match for single-plant operations
            
            # Check if we already created this plant in this session
            pn_lower = plant_name.lower()
            if pn_lower in created_plants:
                return created_plants[pn_lower]
            
            # Skip creating for "all X" patterns - they should match existing plants
            if pn_lower.startswith('all '):
                return None
            
            # Create new plant
            new_pid = str(uuid.uuid4())
            
            # Parse plant name to extract type/variety
            # Common patterns: "Roma Tomatoes", "Tomato (Roma)", "Genovese Basil", "California Wonder Bell Pepper"
            plant_type = plant_name
            variety = None
            
            # Try to extract variety from parentheses: "Tomato (Roma)"
            import re
            paren_match = re.match(r'^(.+?)\s*\((.+?)\)$', plant_name)
            if paren_match:
                plant_type = paren_match.group(1).strip()
                variety = paren_match.group(2).strip()
            else:
                # Known plant types to look for
                known_types = ['tomato', 'tomatoes', 'basil', 'pepper', 'peppers', 'bell pepper', 
                               'lettuce', 'cilantro', 'mint', 'strawberry', 'strawberries', 
                               'jalapeño', 'jalapeno', 'herb', 'herbs']
                
                pn_lower = plant_name.lower()
                found_type = None
                for kt in known_types:
                    if kt in pn_lower:
                        found_type = kt.title()
                        break
                
                if found_type:
                    # Extract variety as everything before the type
                    type_pos = pn_lower.find(found_type.lower())
                    if type_pos > 0:
                        variety = plant_name[:type_pos].strip()
                        plant_type = found_type
                    else:
                        plant_type = found_type
                else:
                    # Fallback: last word is type, rest is variety
                    words = plant_name.split()
                    if len(words) >= 2:
                        plant_type = words[-1]
                        variety = ' '.join(words[:-1])
            
            cursor.execute('''
                INSERT INTO plants (id, name, type, variety, dateAdded, health, 
                                    heightHistory, healthHistory, photos, feedingRecipes, 
                                    feedingApplications, journalEntries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                new_pid, plant_name, plant_type, variety, data.get('date'), 'healthy',
                json.dumps([]), json.dumps([]), json.dumps([]), json.dumps([]), json.dumps([]), json.dumps([])
            ))
            
            # Add to plant_map so subsequent lookups find it
            plant_map[new_pid] = {'name': plant_name, 'type': plant_type, 'variety': variety}
            created_plants[pn_lower] = new_pid
            
            print(f"[AUTO-CREATE] Created new plant: {plant_name} (type={plant_type}, variety={variety})")
            return new_pid
        
        for plant_name in plants_mentioned:
            found = get_or_create_plant(plant_name)
            if found and found not in related_plant_ids:
                related_plant_ids.append(found)

        # Handle actions with improved plant matching
        actions = processed_data.get('actions', [])
        for action in actions:
            plant_name = action.get('plant')
            if not plant_name:
                continue
            
            # Get all matching plants (supports "all tomatoes" pattern)
            matching_pids = get_matching_plant_ids(plant_name)
            
            # If no matches, try to create the plant
            if not matching_pids:
                new_pid = get_or_create_plant(plant_name)
                if new_pid:
                    matching_pids = [new_pid]
            
            # Apply action to ALL matching plants
            for pid in matching_pids:
                plant_row = cursor.execute('SELECT * FROM plants WHERE id = ?', (pid,)).fetchone()
                if not plant_row:
                    continue
            plant = dict(plant_row)
            
            action_type = action.get('action_type')
            
            # Handle height_measurement
            if action_type == 'height_measurement':
                height = action.get('height')
                unit = action.get('unit', 'cm')
                # Convert inches to cm if needed
                if unit.lower() in ['inches', 'inch', 'in', '"']:
                    height = float(height) * 2.54
                    unit = 'cm'
                date = data.get('date') or None
                history = json.loads(plant['heightHistory']) if plant['heightHistory'] else []
                history.append({
                    'id': str(uuid.uuid4()),
                    'date': date,
                    'height': float(height),
                    'unit': unit,
                    'source': 'journal_ai',
                    'notes': action.get('details', '')
                })
                cursor.execute('UPDATE plants SET heightHistory = ? WHERE id = ?', (json.dumps(history), pid))
                
            # Handle feeding
            elif action_type == 'feeding':
                # Create a feeding application in feeding_applications table and link via ID
                app_id = str(uuid.uuid4())
                app_row = {
                    'id': app_id,
                    'recipeId': None,
                    'plantId': pid,
                    'date': data.get('date'),
                    'amount': json.dumps({'value': action.get('amount'), 'unit': action.get('unit', 'unknown')}),
                    'appliedCost': None,
                    'notes': f"AI Logged: {action.get('details')}"
                }
                try:
                    cursor.execute('''
                        INSERT INTO feeding_applications (id, recipeId, plantId, date, amount, appliedCost, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        app_row['id'], app_row['recipeId'], app_row['plantId'], app_row['date'], app_row['amount'], app_row['appliedCost'], app_row['notes']
                    ))
                except Exception as e:
                    # If feedings table insertion fails, just skip
                    print(f"Error inserting feeding application: {e}")
                # Append only the ID to the plant's feedingApplications array
                apps = json.loads(plant['feedingApplications']) if plant['feedingApplications'] else []
                apps.append(app_id)
                cursor.execute('UPDATE plants SET feedingApplications = ? WHERE id = ?', (json.dumps(apps), pid))
                
            # Handle observation, pruning, environmental_adjustment, etc.
            elif action_type in ['observation', 'pruning', 'harvesting', 'watering', 'environmental_adjustment', 'planting']:
                # Add to healthHistory as a general event log
                history = json.loads(plant['healthHistory']) if plant['healthHistory'] else []
                
                note_content = action.get('details', '')
                status = 'neutral'
                
                if action_type == 'observation':
                    # Extract severity if present in details (it was packed into details in the loop above? No, wait)
                    # In the loop above (lines 145-180), we constructed 'processed_data' actions.
                    # But here we are iterating 'processed_data['actions']'.
                    # The 'details' field in 'processed_data' for observation was: f"[{o.get('category', 'general')}] {o.get('observation', '')}"
                    # We don't have severity here easily unless we parse it or change how processed_data is constructed.
                    # But we can just store the note.
                    pass
                
                event_entry = {
                    'id': str(uuid.uuid4()),
                    'date': data.get('date'),
                    'type': action_type,
                    'status': status,
                    'note': f"[{action_type.upper()}] {note_content}",
                    'source': 'journal_ai'
                }
                
                history.append(event_entry)
                cursor.execute('UPDATE plants SET healthHistory = ? WHERE id = ?', (json.dumps(history), pid))
                
                # If it's a critical observation, update the plant's main health status
                if action_type == 'observation' and 'critical' in note_content.lower():
                    cursor.execute('UPDATE plants SET health = ? WHERE id = ?', ('critical', pid))

        # If we have processed_data, store it in tags so UI can render categories
        if processed_data:
            tags = processed_data

    try:
        cursor.execute('''
            INSERT INTO journal_entries (id, date, content, tags, relatedPlantIds, processed_data, processed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data.get('date'), data.get('content'),
            json.dumps(tags),
            json.dumps(related_plant_ids),
            json.dumps(processed_data) if processed_data else None,
            True if processed_data else False
        ))

        # Link journal entry id back to plants' journalEntries
        for p_id in related_plant_ids:
            row = cursor.execute('SELECT journalEntries from plants WHERE id = ?', (p_id,)).fetchone()
            if row and row['journalEntries']:
                j_entries = json.loads(row['journalEntries'])
            else:
                j_entries = []
            if data['id'] not in j_entries:
                j_entries.append(data['id'])
                cursor.execute('UPDATE plants SET journalEntries = ? WHERE id = ?', (json.dumps(j_entries), p_id))

        conn.commit()
        conn.close()
        response_data = data
        response_data['relatedPlantIds'] = related_plant_ids
        response_data['processedData'] = processed_data
        # Include list of auto-created plants
        response_data['createdPlants'] = list(created_plants.keys()) if 'created_plants' in dir() and created_plants else []
        return jsonify(response_data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Products API ---
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    # Parse JSON fields
    result = []
    for p in products:
        p_dict = dict(p)
        p_dict['packageSize'] = json.loads(p_dict['packageSize']) if p_dict['packageSize'] else {}
        result.append(p_dict)
    return jsonify(result)

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    if 'id' not in data:
        data['id'] = str(uuid.uuid4())
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (id, name, brand, category, purchasePrice, packageSize, 
                                  quantityPurchased, quantityRemaining, purchaseDate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['name'], data.get('brand'), data.get('category'), data.get('purchasePrice'),
            json.dumps(data.get('packageSize', {})),
            data.get('quantityPurchased'), data.get('quantityRemaining'), data.get('purchaseDate')
        ))
        conn.commit()
        conn.close()
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<id>', methods=['DELETE', 'PUT'])
def manage_product(id):
    if request.method == 'DELETE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM products WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    elif request.method == 'PUT':
        try:
            data = request.json
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE products
                SET name = ?, brand = ?, category = ?, purchasePrice = ?, 
                    packageSize = ?, quantityPurchased = ?, quantityRemaining = ?, purchaseDate = ?
                WHERE id = ?
            ''', (
                data['name'], data.get('brand'), data.get('category'), data.get('purchasePrice'),
                json.dumps(data.get('packageSize', {})),
                data.get('quantityPurchased'), data.get('quantityRemaining'), data.get('purchaseDate'),
                id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# --- Recipes API ---
@app.route('/api/recipes', methods=['GET'])
def get_recipes():
    conn = get_db_connection()
    recipes = conn.execute('SELECT * FROM feeding_recipes').fetchall()
    conn.close()
    result = []
    for r in recipes:
        r_dict = dict(r)
        r_dict['ingredients'] = json.loads(r_dict['ingredients']) if r_dict['ingredients'] else []
        r_dict['batchSize'] = json.loads(r_dict['batchSize']) if r_dict['batchSize'] else {}
        result.append(r_dict)
    return jsonify(result)

@app.route('/api/recipes', methods=['POST'])
def add_recipe():
    data = request.json
    if 'id' not in data:
        data['id'] = str(uuid.uuid4())
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feeding_recipes (id, name, feedingType, gardenId, ingredients, 
                                         batchSize, schedule, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['name'], data.get('feedingType'), data.get('gardenId'),
            json.dumps(data.get('ingredients', [])),
            json.dumps(data.get('batchSize', {})),
            data.get('schedule'), data.get('notes')
        ))
        conn.commit()
        conn.close()
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<id>', methods=['DELETE', 'PUT'])
def manage_recipe(id):
    if request.method == 'DELETE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM feeding_recipes WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    elif request.method == 'PUT':
        try:
            data = request.json
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE feeding_recipes
                SET name = ?, feedingType = ?, gardenId = ?, ingredients = ?, 
                    batchSize = ?, schedule = ?, notes = ?
                WHERE id = ?
            ''', (
                data['name'], data.get('feedingType'), data.get('gardenId'),
                json.dumps(data.get('ingredients', [])),
                json.dumps(data.get('batchSize', {})),
                data.get('schedule'), data.get('notes'),
                id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# --- Applications API ---
@app.route('/api/applications', methods=['GET'])
def get_applications():
    conn = get_db_connection()
    apps = conn.execute('SELECT * FROM feeding_applications').fetchall()
    conn.close()
    result = []
    for a in apps:
        a_dict = dict(a)
        a_dict['amount'] = json.loads(a_dict['amount']) if a_dict['amount'] else {}
        result.append(a_dict)
    return jsonify(result)

@app.route('/api/applications', methods=['POST'])
def add_application():
    data = request.json
    if 'id' not in data:
        data['id'] = str(uuid.uuid4())
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feeding_applications (id, plantId, recipeId, date, amount, appliedCost, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'], data['plantId'], data['recipeId'], data['date'],
            json.dumps(data.get('amount', {})),
            data.get('appliedCost'), data.get('notes')
        ))
        conn.commit()
        conn.close()
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/applications/<id>', methods=['DELETE', 'PUT'])
def manage_application(id):
    if request.method == 'DELETE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM feeding_applications WHERE id = ?', (id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    elif request.method == 'PUT':
        try:
            data = request.json
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE feeding_applications
                SET plantId = ?, recipeId = ?, date = ?, amount = ?, appliedCost = ?, notes = ?
                WHERE id = ?
            ''', (
                data['plantId'], data['recipeId'], data['date'],
                json.dumps(data.get('amount', {})),
                data.get('appliedCost'), data.get('notes'),
                id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

# --- LLM Integration ---
@app.route('/api/llm/process-journal', methods=['POST'])
def process_journal():
    data = request.json
    journal_text = data.get('text')
    if not journal_text:
        return jsonify({"error": "No text provided"}), 400
    
    try:
        result = llm_service.process_journal_entry(journal_text)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
