"""
Markdown File Service for Smart Garden Dashboard
Provides Obsidian-compatible storage using YAML frontmatter
"""

import os
import frontmatter
from datetime import datetime
from pathlib import Path
import json
import re
from typing import Optional, List, Dict, Any
import uuid

# Default storage path - can be overridden to point to Obsidian vault
MD_STORAGE_PATH = os.environ.get('GARDEN_MD_PATH', './garden-data')


def get_storage_path() -> Path:
    """Get the base storage path for MD files"""
    return Path(MD_STORAGE_PATH)


def ensure_directories():
    """Create all required directories if they don't exist"""
    base = get_storage_path()
    directories = [
        'plants',
        'logs/growth',
        'logs/watering',
        'logs/fertilization',
        'logs/harvest',
        'logs/pest',
        'recipes',
        'budget/products',
        'tasks',
        'weather',
        'notes'
    ]
    for dir_path in directories:
        (base / dir_path).mkdir(parents=True, exist_ok=True)
    return base


def sanitize_filename(name: str) -> str:
    """Convert a name to a safe filename"""
    # Remove or replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    safe = safe.replace(' ', '-')
    return safe.lower()


def generate_id() -> str:
    """Generate a unique ID for new records"""
    return str(uuid.uuid4())[:8]


# ============== Core MD File Operations ==============

def read_md_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Read a Markdown file and return its frontmatter and content.
    Returns dict with 'metadata' (frontmatter) and 'content' (body).
    """
    try:
        if not filepath.exists():
            return None
        
        post = frontmatter.load(filepath)
        return {
            'metadata': dict(post.metadata),
            'content': post.content,
            '_filepath': str(filepath)
        }
    except Exception as e:
        print(f"Error reading MD file {filepath}: {e}")
        return None


def write_md_file(filepath: Path, metadata: Dict[str, Any], content: str = "") -> bool:
    """
    Write a Markdown file with YAML frontmatter.
    """
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Create frontmatter post
        post = frontmatter.Post(content, **metadata)
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))
        
        return True
    except Exception as e:
        print(f"Error writing MD file {filepath}: {e}")
        return False


def update_md_file(filepath: Path, updates: Dict[str, Any], content: Optional[str] = None) -> bool:
    """
    Update specific fields in a Markdown file's frontmatter.
    Optionally update the content body.
    """
    existing = read_md_file(filepath)
    if not existing:
        return False
    
    # Merge metadata
    new_metadata = {**existing['metadata'], **updates}
    new_content = content if content is not None else existing['content']
    
    return write_md_file(filepath, new_metadata, new_content)


def delete_md_file(filepath: Path) -> bool:
    """Delete a Markdown file"""
    try:
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    except Exception as e:
        print(f"Error deleting MD file {filepath}: {e}")
        return False


def list_md_files(directory: Path, filter_tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    List all Markdown files in a directory.
    Optionally filter by tags in frontmatter.
    """
    results = []
    
    if not directory.exists():
        return results
    
    for filepath in directory.glob('*.md'):
        data = read_md_file(filepath)
        if data:
            # Apply tag filter if specified
            if filter_tags:
                file_tags = data['metadata'].get('tags', [])
                if not any(tag in file_tags for tag in filter_tags):
                    continue
            results.append(data)
    
    return results


def search_md_files(query: str, directory: Path, search_content: bool = True) -> List[Dict[str, Any]]:
    """
    Search Markdown files for a query string.
    Searches in frontmatter values and optionally in content.
    """
    results = []
    query_lower = query.lower()
    
    if not directory.exists():
        return results
    
    for filepath in directory.rglob('*.md'):
        data = read_md_file(filepath)
        if not data:
            continue
        
        # Search in frontmatter
        found = False
        for key, value in data['metadata'].items():
            if isinstance(value, str) and query_lower in value.lower():
                found = True
                break
        
        # Search in content
        if not found and search_content:
            if query_lower in data['content'].lower():
                found = True
        
        if found:
            results.append(data)
    
    return results


# ============== Plant Operations ==============

def get_plant_filepath(plant_id: str) -> Path:
    """Get the filepath for a plant by ID"""
    base = get_storage_path()
    # Search for the plant file
    for filepath in (base / 'plants').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == plant_id:
            return filepath
    return base / 'plants' / f'{plant_id}.md'


def create_plant(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new plant MD file"""
    base = get_storage_path()
    ensure_directories()
    
    # Generate ID and unique code
    plant_id = generate_id()
    name = data.get('name', 'Unknown')
    variety = data.get('variety', '')
    instance_number = data.get('instance_number', 1)
    
    # Generate unique code (e.g., TOM-001)
    code_prefix = name[:3].upper()
    unique_code = f"{code_prefix}-{instance_number:03d}"
    
    # Create filename
    filename = sanitize_filename(f"{name}-{instance_number}")
    filepath = base / 'plants' / f'{filename}.md'
    
    # Handle duplicates
    counter = 1
    while filepath.exists():
        filepath = base / 'plants' / f'{filename}-{counter}.md'
        counter += 1
    
    now = datetime.now().isoformat()
    
    metadata = {
        'id': plant_id,
        'name': name,
        'variety': variety,
        'instance_number': instance_number,
        'unique_code': unique_code,
        'location': data.get('location', ''),
        'date_planted': data.get('date_planted', ''),
        'date_germinated': data.get('date_germinated', ''),
        'expected_harvest': data.get('expected_harvest', ''),
        'status': data.get('status', 'active'),
        'image_url': data.get('image_url', ''),
        'created_at': now,
        'updated_at': now,
        'tags': ['plant', name.lower()]
    }
    
    # Build display name
    display_name = f"{name} #{instance_number}" if instance_number else name
    
    content = f"""# {display_name}

## Notes
{data.get('notes', 'No notes yet.')}

## Quick Links
- Growth Logs: [[logs/growth/{unique_code}|View Growth History]]
- Watering: [[logs/watering/{unique_code}|View Watering History]]
"""
    
    if write_md_file(filepath, metadata, content):
        return {**metadata, 'display_name': display_name, 'content': content, '_filepath': str(filepath)}
    return None


def get_plant(plant_id: str) -> Optional[Dict[str, Any]]:
    """Get a plant by ID"""
    base = get_storage_path()
    for filepath in (base / 'plants').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == plant_id:
            meta = data['metadata']
            meta['display_name'] = f"{meta['name']} #{meta.get('instance_number', 1)}"
            return {**meta, 'content': data['content'], '_filepath': str(filepath)}
    return None


def get_plant_by_code(code: str) -> Optional[Dict[str, Any]]:
    """Get a plant by unique code"""
    base = get_storage_path()
    for filepath in (base / 'plants').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('unique_code', '').upper() == code.upper():
            meta = data['metadata']
            meta['display_name'] = f"{meta['name']} #{meta.get('instance_number', 1)}"
            return {**meta, 'content': data['content'], '_filepath': str(filepath)}
    return None


def list_plants(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all plants, optionally filtered by status"""
    base = get_storage_path()
    plants = []
    
    for filepath in (base / 'plants').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            meta = data['metadata']
            if status and meta.get('status') != status:
                continue
            meta['display_name'] = f"{meta['name']} #{meta.get('instance_number', 1)}"
            # Include related data
            meta['growth_logs'] = get_growth_logs(meta['id'])
            meta['waterings'] = get_waterings(meta['id'])
            meta['fertilizations'] = get_fertilizations(meta['id'])
            meta['harvests'] = get_harvests(meta['id'])
            meta['pest_issues'] = get_pest_issues(meta['id'])
            plants.append(meta)
    
    return sorted(plants, key=lambda x: x.get('created_at', ''), reverse=True)


def update_plant(plant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a plant's metadata"""
    base = get_storage_path()
    for filepath in (base / 'plants').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == plant_id:
            updates['updated_at'] = datetime.now().isoformat()
            if update_md_file(filepath, updates):
                return get_plant(plant_id)
    return None


def delete_plant(plant_id: str) -> bool:
    """Delete a plant"""
    base = get_storage_path()
    for filepath in (base / 'plants').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == plant_id:
            return delete_md_file(filepath)
    return False


def get_next_instance_number(name: str, variety: str = None) -> int:
    """Get the next instance number for a plant name/variety combo"""
    base = get_storage_path()
    max_instance = 0
    
    for filepath in (base / 'plants').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            meta = data['metadata']
            if meta.get('name', '').lower() == name.lower():
                if variety is None or meta.get('variety', '').lower() == (variety or '').lower():
                    instance = meta.get('instance_number', 0)
                    if instance > max_instance:
                        max_instance = instance
    
    return max_instance + 1


# ============== Growth Log Operations ==============

def create_growth_log(plant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new growth log for a plant"""
    base = get_storage_path()
    ensure_directories()
    
    plant = get_plant(plant_id)
    if not plant:
        return None
    
    log_id = generate_id()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    metadata = {
        'id': log_id,
        'plant_id': plant_id,
        'plant_code': plant.get('unique_code', ''),
        'date': data.get('date', now.isoformat()),
        'height_cm': data.get('height_cm'),
        'width_cm': data.get('width_cm'),
        'leaf_count': data.get('leaf_count'),
        'health_rating': data.get('health_rating'),
        'image_url': data.get('image_url', ''),
        'tags': ['growth-log', plant.get('name', '').lower()]
    }
    
    content = f"""# Growth Log - {plant.get('display_name', '')}

**Date:** {date_str}

## Measurements
- Height: {data.get('height_cm', 'N/A')} cm
- Width: {data.get('width_cm', 'N/A')} cm
- Leaf Count: {data.get('leaf_count', 'N/A')}
- Health Rating: {data.get('health_rating', 'N/A')}/10

## Notes
{data.get('notes', 'No notes.')}

---
Plant: [[plants/{plant.get('unique_code', '')}|{plant.get('display_name', '')}]]
"""
    
    filename = f"{date_str}-{plant.get('unique_code', log_id)}"
    filepath = base / 'logs' / 'growth' / f'{filename}.md'
    
    # Handle duplicates
    counter = 1
    while filepath.exists():
        filepath = base / 'logs' / 'growth' / f'{filename}-{counter}.md'
        counter += 1
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_growth_logs(plant_id: str) -> List[Dict[str, Any]]:
    """Get all growth logs for a plant"""
    base = get_storage_path()
    logs = []
    
    for filepath in (base / 'logs' / 'growth').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('plant_id') == plant_id:
            logs.append(data['metadata'])
    
    return sorted(logs, key=lambda x: x.get('date', ''), reverse=True)


# ============== Watering Operations ==============

def create_watering(plant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new watering log for a plant"""
    base = get_storage_path()
    ensure_directories()
    
    plant = get_plant(plant_id)
    if not plant:
        return None
    
    log_id = generate_id()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    # Handle recipe-based watering
    recipe_id = data.get('recipe_id')
    ingredients = data.get('ingredients', [])
    total_cost = data.get('total_cost', 0)
    
    # Calculate cost from ingredients if provided
    if ingredients and not total_cost:
        for ing in ingredients:
            total_cost += ing.get('cost', 0)
    
    metadata = {
        'id': log_id,
        'plant_id': plant_id,
        'plant_code': plant.get('unique_code', ''),
        'date': data.get('date', now.isoformat()),
        'amount_ml': data.get('amount_ml'),
        'amount_value': data.get('amount_value'),  # For gallons, cups, etc.
        'amount_unit': data.get('amount_unit', 'ml'),
        'method': data.get('method', 'watering can'),
        'recipe_id': recipe_id,
        'recipe_name': data.get('recipe_name', ''),
        'ingredients': ingredients,
        'total_cost': total_cost,
        'tags': ['watering', plant.get('name', '').lower()]
    }
    
    # Build ingredient list for content
    ingredient_text = ""
    if ingredients:
        ingredient_text = "\n## Ingredients Used\n"
        for ing in ingredients:
            ingredient_text += f"- {ing.get('name', 'Unknown')}: {ing.get('amount', '')} {ing.get('unit', '')}\n"
    
    content = f"""# Watering Log - {plant.get('display_name', '')}

**Date:** {date_str}
**Method:** {data.get('method', 'watering can')}
**Amount:** {data.get('amount_ml') or data.get('amount_value', 'N/A')} {data.get('amount_unit', 'ml')}
{f"**Recipe:** [[recipes/{recipe_id}|{data.get('recipe_name', '')}]]" if recipe_id else ""}
{f"**Cost:** ${total_cost:.2f}" if total_cost else ""}
{ingredient_text}
## Notes
{data.get('notes', 'No notes.')}

---
Plant: [[plants/{plant.get('unique_code', '')}|{plant.get('display_name', '')}]]
"""
    
    filename = f"{date_str}-{plant.get('unique_code', log_id)}-water"
    filepath = base / 'logs' / 'watering' / f'{filename}.md'
    
    # Handle duplicates
    counter = 1
    while filepath.exists():
        filepath = base / 'logs' / 'watering' / f'{filename}-{counter}.md'
        counter += 1
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_waterings(plant_id: str) -> List[Dict[str, Any]]:
    """Get all watering logs for a plant"""
    base = get_storage_path()
    logs = []
    
    for filepath in (base / 'logs' / 'watering').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('plant_id') == plant_id:
            logs.append(data['metadata'])
    
    return sorted(logs, key=lambda x: x.get('date', ''), reverse=True)


def get_all_waterings() -> List[Dict[str, Any]]:
    """Get all watering logs"""
    base = get_storage_path()
    logs = []
    
    for filepath in (base / 'logs' / 'watering').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            logs.append(data['metadata'])
    
    return sorted(logs, key=lambda x: x.get('date', ''), reverse=True)


# ============== Fertilization Operations ==============

def create_fertilization(plant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new fertilization log"""
    base = get_storage_path()
    ensure_directories()
    
    plant = get_plant(plant_id)
    if not plant:
        return None
    
    log_id = generate_id()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    metadata = {
        'id': log_id,
        'plant_id': plant_id,
        'plant_code': plant.get('unique_code', ''),
        'date': data.get('date', now.isoformat()),
        'fertilizer_type': data.get('fertilizer_type', ''),
        'product_id': data.get('product_id'),
        'amount': data.get('amount', ''),
        'amount_value': data.get('amount_value'),
        'amount_unit': data.get('amount_unit', ''),
        'npk_ratio': data.get('npk_ratio', ''),
        'cost': data.get('cost', 0),
        'tags': ['fertilization', plant.get('name', '').lower()]
    }
    
    content = f"""# Fertilization Log - {plant.get('display_name', '')}

**Date:** {date_str}
**Type:** {data.get('fertilizer_type', 'Unknown')}
**Amount:** {data.get('amount', 'N/A')}
**NPK:** {data.get('npk_ratio', 'N/A')}
{f"**Cost:** ${data.get('cost', 0):.2f}" if data.get('cost') else ""}

## Notes
{data.get('notes', 'No notes.')}

---
Plant: [[plants/{plant.get('unique_code', '')}|{plant.get('display_name', '')}]]
"""
    
    filename = f"{date_str}-{plant.get('unique_code', log_id)}-fert"
    filepath = base / 'logs' / 'fertilization' / f'{filename}.md'
    
    counter = 1
    while filepath.exists():
        filepath = base / 'logs' / 'fertilization' / f'{filename}-{counter}.md'
        counter += 1
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_fertilizations(plant_id: str) -> List[Dict[str, Any]]:
    """Get all fertilization logs for a plant"""
    base = get_storage_path()
    logs = []
    
    for filepath in (base / 'logs' / 'fertilization').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('plant_id') == plant_id:
            logs.append(data['metadata'])
    
    return sorted(logs, key=lambda x: x.get('date', ''), reverse=True)


# ============== Harvest Operations ==============

def create_harvest(plant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new harvest log"""
    base = get_storage_path()
    ensure_directories()
    
    plant = get_plant(plant_id)
    if not plant:
        return None
    
    log_id = generate_id()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    metadata = {
        'id': log_id,
        'plant_id': plant_id,
        'plant_code': plant.get('unique_code', ''),
        'plant_name': plant.get('display_name', ''),
        'date': data.get('date', now.isoformat()),
        'quantity': data.get('quantity'),
        'unit': data.get('unit', 'pieces'),
        'quality_rating': data.get('quality_rating'),
        'tags': ['harvest', plant.get('name', '').lower()]
    }
    
    content = f"""# Harvest Log - {plant.get('display_name', '')}

**Date:** {date_str}
**Quantity:** {data.get('quantity', 'N/A')} {data.get('unit', 'pieces')}
**Quality:** {data.get('quality_rating', 'N/A')}/10

## Notes
{data.get('notes', 'No notes.')}

---
Plant: [[plants/{plant.get('unique_code', '')}|{plant.get('display_name', '')}]]
"""
    
    filename = f"{date_str}-{plant.get('unique_code', log_id)}-harvest"
    filepath = base / 'logs' / 'harvest' / f'{filename}.md'
    
    counter = 1
    while filepath.exists():
        filepath = base / 'logs' / 'harvest' / f'{filename}-{counter}.md'
        counter += 1
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_harvests(plant_id: str = None) -> List[Dict[str, Any]]:
    """Get harvest logs, optionally filtered by plant"""
    base = get_storage_path()
    logs = []
    
    for filepath in (base / 'logs' / 'harvest').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            if plant_id and data['metadata'].get('plant_id') != plant_id:
                continue
            logs.append(data['metadata'])
    
    return sorted(logs, key=lambda x: x.get('date', ''), reverse=True)


# ============== Pest Issue Operations ==============

def create_pest_issue(plant_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new pest issue log"""
    base = get_storage_path()
    ensure_directories()
    
    plant = get_plant(plant_id)
    if not plant:
        return None
    
    log_id = generate_id()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    metadata = {
        'id': log_id,
        'plant_id': plant_id,
        'plant_code': plant.get('unique_code', ''),
        'date_identified': data.get('date_identified', now.isoformat()),
        'pest_type': data.get('pest_type', ''),
        'severity': data.get('severity', 'mild'),
        'treatment': data.get('treatment', ''),
        'resolved': data.get('resolved', False),
        'date_resolved': data.get('date_resolved'),
        'tags': ['pest', plant.get('name', '').lower()]
    }
    
    content = f"""# Pest Issue - {plant.get('display_name', '')}

**Date Identified:** {date_str}
**Pest Type:** {data.get('pest_type', 'Unknown')}
**Severity:** {data.get('severity', 'mild')}
**Status:** {'Resolved' if data.get('resolved') else 'Active'}

## Treatment
{data.get('treatment', 'No treatment recorded.')}

## Notes
{data.get('notes', 'No notes.')}

---
Plant: [[plants/{plant.get('unique_code', '')}|{plant.get('display_name', '')}]]
"""
    
    filename = f"{date_str}-{plant.get('unique_code', log_id)}-pest"
    filepath = base / 'logs' / 'pest' / f'{filename}.md'
    
    counter = 1
    while filepath.exists():
        filepath = base / 'logs' / 'pest' / f'{filename}-{counter}.md'
        counter += 1
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_pest_issues(plant_id: str = None, active_only: bool = False) -> List[Dict[str, Any]]:
    """Get pest issues, optionally filtered"""
    base = get_storage_path()
    logs = []
    
    for filepath in (base / 'logs' / 'pest').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            meta = data['metadata']
            if plant_id and meta.get('plant_id') != plant_id:
                continue
            if active_only and meta.get('resolved'):
                continue
            logs.append(meta)
    
    return sorted(logs, key=lambda x: x.get('date_identified', ''), reverse=True)


# ============== Task Operations ==============

def create_task(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new task"""
    base = get_storage_path()
    ensure_directories()
    
    task_id = generate_id()
    now = datetime.now()
    
    metadata = {
        'id': task_id,
        'title': data.get('title', 'Untitled Task'),
        'description': data.get('description', ''),
        'task_type': data.get('task_type', 'other'),
        'plant_id': data.get('plant_id'),
        'due_date': data.get('due_date'),
        'recurring': data.get('recurring', False),
        'recurrence_interval': data.get('recurrence_interval'),
        'completed': False,
        'completed_date': None,
        'priority': data.get('priority', 'medium'),
        'created_at': now.isoformat(),
        'tags': ['task', data.get('task_type', 'other')]
    }
    
    content = f"""# {data.get('title', 'Untitled Task')}

**Type:** {data.get('task_type', 'other')}
**Priority:** {data.get('priority', 'medium')}
**Due:** {data.get('due_date', 'No due date')}
**Status:** Pending

## Description
{data.get('description', 'No description.')}
"""
    
    filename = sanitize_filename(f"task-{task_id}")
    filepath = base / 'tasks' / f'{filename}.md'
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get a task by ID"""
    base = get_storage_path()
    for filepath in (base / 'tasks').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == task_id:
            return data['metadata']
    return None


def list_tasks(completed: bool = None) -> List[Dict[str, Any]]:
    """List all tasks, optionally filtered by completion status"""
    base = get_storage_path()
    tasks = []
    
    for filepath in (base / 'tasks').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            meta = data['metadata']
            if completed is not None and meta.get('completed') != completed:
                continue
            tasks.append(meta)
    
    return sorted(tasks, key=lambda x: x.get('due_date') or '9999', reverse=False)


def complete_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Mark a task as completed"""
    base = get_storage_path()
    for filepath in (base / 'tasks').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == task_id:
            updates = {
                'completed': True,
                'completed_date': datetime.now().isoformat()
            }
            if update_md_file(filepath, updates):
                return get_task(task_id)
    return None


def delete_task(task_id: str) -> bool:
    """Delete a task"""
    base = get_storage_path()
    for filepath in (base / 'tasks').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == task_id:
            return delete_md_file(filepath)
    return False


# ============== Weather Operations ==============

def create_weather_log(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new weather log"""
    base = get_storage_path()
    ensure_directories()
    
    log_id = generate_id()
    now = datetime.now()
    date_str = data.get('date', now.strftime('%Y-%m-%d'))
    
    metadata = {
        'id': log_id,
        'date': date_str,
        'temperature_high': data.get('temperature_high'),
        'temperature_low': data.get('temperature_low'),
        'humidity': data.get('humidity'),
        'rainfall_mm': data.get('rainfall_mm'),
        'conditions': data.get('conditions', ''),
        'tags': ['weather']
    }
    
    content = f"""# Weather Log - {date_str}

**High:** {data.get('temperature_high', 'N/A')}°
**Low:** {data.get('temperature_low', 'N/A')}°
**Humidity:** {data.get('humidity', 'N/A')}%
**Rainfall:** {data.get('rainfall_mm', 'N/A')}mm
**Conditions:** {data.get('conditions', 'Unknown')}

## Notes
{data.get('notes', 'No notes.')}
"""
    
    filename = f"{date_str}"
    filepath = base / 'weather' / f'{filename}.md'
    
    # For weather, we might want to update existing day's entry
    if filepath.exists():
        if update_md_file(filepath, metadata, content):
            return metadata
    else:
        if write_md_file(filepath, metadata, content):
            return metadata
    return None


def list_weather_logs() -> List[Dict[str, Any]]:
    """List all weather logs"""
    base = get_storage_path()
    logs = []
    
    for filepath in (base / 'weather').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            logs.append(data['metadata'])
    
    return sorted(logs, key=lambda x: x.get('date', ''), reverse=True)


# ============== Garden Note Operations ==============

def create_note(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new garden note"""
    base = get_storage_path()
    ensure_directories()
    
    note_id = generate_id()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    
    metadata = {
        'id': note_id,
        'raw_text': data.get('raw_text', ''),
        'processed': data.get('processed', False),
        'extracted_data': data.get('extracted_data', []),
        'created_at': now.isoformat(),
        'tags': ['note']
    }
    
    content = f"""# Garden Note - {date_str}

{data.get('raw_text', '')}
"""
    
    filename = f"{date_str}-{note_id}"
    filepath = base / 'notes' / f'{filename}.md'
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def list_notes() -> List[Dict[str, Any]]:
    """List all garden notes"""
    base = get_storage_path()
    notes_list = []
    
    for filepath in (base / 'notes').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            notes_list.append(data['metadata'])
    
    return sorted(notes_list, key=lambda x: x.get('created_at', ''), reverse=True)


def update_note(note_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a note"""
    base = get_storage_path()
    for filepath in (base / 'notes').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == note_id:
            if update_md_file(filepath, updates):
                # Return updated note
                return read_md_file(filepath)['metadata']
    return None


# ============== Recipe Operations ==============

def create_recipe(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new compost tea / nutrient recipe"""
    base = get_storage_path()
    ensure_directories()
    
    recipe_id = generate_id()
    now = datetime.now()
    
    # Calculate total cost from ingredients
    ingredients = data.get('ingredients', [])
    total_cost = sum(ing.get('cost', 0) for ing in ingredients)
    
    metadata = {
        'id': recipe_id,
        'name': data.get('name', 'Untitled Recipe'),
        'type': data.get('type', 'compost_tea'),
        'description': data.get('description', ''),
        'ingredients': ingredients,
        'instructions': data.get('instructions', ''),
        'brew_time_hours': data.get('brew_time_hours'),
        'yield_amount': data.get('yield_amount'),
        'yield_unit': data.get('yield_unit', 'gallons'),
        'total_cost': total_cost,
        'created_at': now.isoformat(),
        'tags': ['recipe', data.get('type', 'compost_tea')]
    }
    
    # Build ingredient table for MD content
    ingredient_table = "| Ingredient | Amount | Unit | Cost |\n|------------|--------|------|------|\n"
    for ing in ingredients:
        ingredient_table += f"| {ing.get('name', '')} | {ing.get('amount', '')} | {ing.get('unit', '')} | ${ing.get('cost', 0):.2f} |\n"
    
    content = f"""# {data.get('name', 'Untitled Recipe')}

**Type:** {data.get('type', 'compost_tea')}
**Yield:** {data.get('yield_amount', 'N/A')} {data.get('yield_unit', 'gallons')}
**Brew Time:** {data.get('brew_time_hours', 'N/A')} hours
**Total Cost:** ${total_cost:.2f}

## Ingredients
{ingredient_table}

## Instructions
{data.get('instructions', 'No instructions provided.')}

## Notes
{data.get('description', '')}
"""
    
    filename = sanitize_filename(data.get('name', f'recipe-{recipe_id}'))
    filepath = base / 'recipes' / f'{filename}.md'
    
    counter = 1
    while filepath.exists():
        filepath = base / 'recipes' / f'{filename}-{counter}.md'
        counter += 1
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_recipe(recipe_id: str) -> Optional[Dict[str, Any]]:
    """Get a recipe by ID"""
    base = get_storage_path()
    for filepath in (base / 'recipes').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == recipe_id:
            return {**data['metadata'], 'content': data['content']}
    return None


def list_recipes(recipe_type: str = None) -> List[Dict[str, Any]]:
    """List all recipes, optionally filtered by type"""
    base = get_storage_path()
    recipes = []
    
    for filepath in (base / 'recipes').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            meta = data['metadata']
            if recipe_type and meta.get('type') != recipe_type:
                continue
            recipes.append(meta)
    
    return sorted(recipes, key=lambda x: x.get('name', ''))


def update_recipe(recipe_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a recipe"""
    base = get_storage_path()
    for filepath in (base / 'recipes').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == recipe_id:
            # Recalculate total cost if ingredients changed
            if 'ingredients' in updates:
                updates['total_cost'] = sum(ing.get('cost', 0) for ing in updates['ingredients'])
            if update_md_file(filepath, updates):
                return get_recipe(recipe_id)
    return None


def delete_recipe(recipe_id: str) -> bool:
    """Delete a recipe"""
    base = get_storage_path()
    for filepath in (base / 'recipes').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == recipe_id:
            return delete_md_file(filepath)
    return False


# ============== Budget/Product Operations ==============

def create_product(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new nutrient/product for budget tracking"""
    base = get_storage_path()
    ensure_directories()
    
    product_id = generate_id()
    now = datetime.now()
    
    # Calculate price per unit
    size_amount = data.get('size_amount', 1)
    purchase_price = data.get('purchase_price', 0)
    price_per_unit = purchase_price / size_amount if size_amount else 0
    
    metadata = {
        'id': product_id,
        'name': data.get('name', 'Unknown Product'),
        'brand': data.get('brand', ''),
        'category': data.get('category', 'fertilizer'),  # fertilizer, amendment, pesticide, tool, etc.
        'size_amount': size_amount,
        'size_unit': data.get('size_unit', 'oz'),
        'purchase_price': purchase_price,
        'price_per_unit': price_per_unit,
        'npk_ratio': data.get('npk_ratio', ''),
        'purchase_date': data.get('purchase_date', now.strftime('%Y-%m-%d')),
        'created_at': now.isoformat(),
        'tags': ['budget', 'product', data.get('category', 'fertilizer')]
    }
    
    content = f"""# {data.get('name', 'Unknown Product')}

**Brand:** {data.get('brand', 'N/A')}
**Category:** {data.get('category', 'fertilizer')}
**Size:** {size_amount} {data.get('size_unit', 'oz')}
**Price:** ${purchase_price:.2f}
**Price per {data.get('size_unit', 'unit')}:** ${price_per_unit:.2f}
**NPK:** {data.get('npk_ratio', 'N/A')}
**Purchased:** {data.get('purchase_date', 'Unknown')}

## Notes
{data.get('notes', '')}
"""
    
    filename = sanitize_filename(f"{data.get('brand', '')}-{data.get('name', product_id)}")
    filepath = base / 'budget' / 'products' / f'{filename}.md'
    
    counter = 1
    while filepath.exists():
        filepath = base / 'budget' / 'products' / f'{filename}-{counter}.md'
        counter += 1
    
    if write_md_file(filepath, metadata, content):
        return metadata
    return None


def get_product(product_id: str) -> Optional[Dict[str, Any]]:
    """Get a product by ID"""
    base = get_storage_path()
    for filepath in (base / 'budget' / 'products').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == product_id:
            return data['metadata']
    return None


def list_products(category: str = None) -> List[Dict[str, Any]]:
    """List all products, optionally filtered by category"""
    base = get_storage_path()
    products = []
    
    for filepath in (base / 'budget' / 'products').glob('*.md'):
        data = read_md_file(filepath)
        if data:
            meta = data['metadata']
            if category and meta.get('category') != category:
                continue
            products.append(meta)
    
    return sorted(products, key=lambda x: x.get('name', ''))


def update_product(product_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a product"""
    base = get_storage_path()
    for filepath in (base / 'budget' / 'products').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == product_id:
            # Recalculate price per unit if needed
            if 'size_amount' in updates or 'purchase_price' in updates:
                size = updates.get('size_amount', data['metadata'].get('size_amount', 1))
                price = updates.get('purchase_price', data['metadata'].get('purchase_price', 0))
                updates['price_per_unit'] = price / size if size else 0
            if update_md_file(filepath, updates):
                return get_product(product_id)
    return None


def delete_product(product_id: str) -> bool:
    """Delete a product"""
    base = get_storage_path()
    for filepath in (base / 'budget' / 'products').glob('*.md'):
        data = read_md_file(filepath)
        if data and data['metadata'].get('id') == product_id:
            return delete_md_file(filepath)
    return False


def get_budget_summary() -> Dict[str, Any]:
    """Get budget summary with totals and by category"""
    products = list_products()
    recipes = list_recipes()
    
    total_spent = sum(p.get('price', p.get('purchase_price', 0)) for p in products)
    
    # Group by category
    by_category = {}
    for p in products:
        cat = p.get('category', 'other')
        if cat not in by_category:
            by_category[cat] = {'count': 0, 'total': 0}
        by_category[cat]['count'] += 1
        by_category[cat]['total'] += p.get('price', p.get('purchase_price', 0))
    
    # Monthly spending (from purchase dates)
    monthly = {}
    for p in products:
        date = p.get('purchase_date', '')
        if date:
            month = date[:7]  # YYYY-MM
            if month not in monthly:
                monthly[month] = 0
            monthly[month] += p.get('price', p.get('purchase_price', 0))
    
    return {
        'total_spent': total_spent,
        'total_products': len(products),
        'active_recipes': len(recipes),
        'product_count': len(products),
        'by_category': by_category,
        'monthly_spending': monthly
    }


def get_cost_per_plant(plant_id: str) -> Dict[str, Any]:
    """Calculate total cost invested in a specific plant"""
    waterings = get_waterings(plant_id)
    fertilizations = get_fertilizations(plant_id)
    
    watering_cost = sum(w.get('total_cost', 0) for w in waterings)
    fert_cost = sum(f.get('cost', 0) for f in fertilizations)
    
    return {
        'plant_id': plant_id,
        'watering_cost': watering_cost,
        'fertilization_cost': fert_cost,
        'total_cost': watering_cost + fert_cost,
        'watering_count': len(waterings),
        'fertilization_count': len(fertilizations)
    }


# ============== Chart Data Operations ==============

def get_growth_chart_data(plant_id: str) -> Dict[str, Any]:
    """Get growth data formatted for charts"""
    logs = get_growth_logs(plant_id)
    logs = sorted(logs, key=lambda x: x.get('date', ''))
    
    return {
        'dates': [l.get('date', '')[:10] for l in logs],
        'heights': [l.get('height_cm') for l in logs],
        'widths': [l.get('width_cm') for l in logs],
        'leaf_counts': [l.get('leaf_count') for l in logs],
        'health_ratings': [l.get('health_rating') for l in logs]
    }


def get_watering_chart_data(plant_id: str = None) -> Dict[str, Any]:
    """Get watering data formatted for charts"""
    if plant_id:
        logs = get_waterings(plant_id)
    else:
        logs = get_all_waterings()
    
    logs = sorted(logs, key=lambda x: x.get('date', ''))
    
    return {
        'dates': [l.get('date', '')[:10] for l in logs],
        'amounts': [l.get('amount_ml') or l.get('amount_value', 0) for l in logs],
        'costs': [l.get('total_cost', 0) for l in logs],
        'methods': [l.get('method', '') for l in logs],
        'recipes': [l.get('recipe_name', '') for l in logs]
    }


def get_budget_chart_data() -> Dict[str, Any]:
    """Get budget data formatted for charts"""
    summary = get_budget_summary()
    
    # Category breakdown - return as dict for frontend
    by_category = {cat: data['total'] for cat, data in summary['by_category'].items()}
    
    return {
        'by_category': by_category,
        'by_month': summary['monthly_spending'],
        'total_spent': summary['total_spent']
    }


# Initialize storage on import
ensure_directories()
