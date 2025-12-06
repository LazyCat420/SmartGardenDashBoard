"""
Smart Garden Dashboard - Flask Backend
Main application with REST API endpoints
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
CORS(app)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'garden.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ============== Database Models ==============

class Plant(db.Model):
    """Model for tracking plants in the garden"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    variety = db.Column(db.String(100))
    location = db.Column(db.String(100))  # bed, pot, greenhouse
    date_planted = db.Column(db.DateTime)
    date_germinated = db.Column(db.DateTime)
    expected_harvest = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='active')  # active, harvested, removed
    notes = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    growth_logs = db.relationship('GrowthLog', backref='plant', lazy=True, cascade='all, delete-orphan')
    waterings = db.relationship('Watering', backref='plant', lazy=True, cascade='all, delete-orphan')
    fertilizations = db.relationship('Fertilization', backref='plant', lazy=True, cascade='all, delete-orphan')
    harvests = db.relationship('Harvest', backref='plant', lazy=True, cascade='all, delete-orphan')
    pest_issues = db.relationship('PestIssue', backref='plant', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'variety': self.variety,
            'location': self.location,
            'date_planted': self.date_planted.isoformat() if self.date_planted else None,
            'date_germinated': self.date_germinated.isoformat() if self.date_germinated else None,
            'expected_harvest': self.expected_harvest.isoformat() if self.expected_harvest else None,
            'status': self.status,
            'notes': self.notes,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'growth_logs': [log.to_dict() for log in self.growth_logs],
            'waterings': [w.to_dict() for w in self.waterings[-5:]],  # Last 5
            'fertilizations': [f.to_dict() for f in self.fertilizations[-5:]],
            'harvests': [h.to_dict() for h in self.harvests],
            'pest_issues': [p.to_dict() for p in self.pest_issues]
        }


class GrowthLog(db.Model):
    """Model for tracking plant growth over time"""
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    height_cm = db.Column(db.Float)
    width_cm = db.Column(db.Float)
    leaf_count = db.Column(db.Integer)
    health_rating = db.Column(db.Integer)  # 1-10
    notes = db.Column(db.Text)
    image_url = db.Column(db.String(500))

    def to_dict(self):
        return {
            'id': self.id,
            'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'height_cm': self.height_cm,
            'width_cm': self.width_cm,
            'leaf_count': self.leaf_count,
            'health_rating': self.health_rating,
            'notes': self.notes,
            'image_url': self.image_url
        }


class Watering(db.Model):
    """Model for tracking watering events"""
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    amount_ml = db.Column(db.Float)
    method = db.Column(db.String(50))  # compost tea, spray, soak, etc.
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'amount_ml': self.amount_ml,
            'method': self.method,
            'notes': self.notes
        }


class Fertilization(db.Model):
    """Model for tracking fertilization events"""
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    fertilizer_type = db.Column(db.String(100))
    amount = db.Column(db.String(50))
    npk_ratio = db.Column(db.String(20))  # e.g., "10-10-10"
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'fertilizer_type': self.fertilizer_type,
            'amount': self.amount,
            'npk_ratio': self.npk_ratio,
            'notes': self.notes
        }


class Harvest(db.Model):
    """Model for tracking harvest events"""
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20))  # kg, lbs, pieces, bunches
    quality_rating = db.Column(db.Integer)  # 1-10
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'quantity': self.quantity,
            'unit': self.unit,
            'quality_rating': self.quality_rating,
            'notes': self.notes
        }


class PestIssue(db.Model):
    """Model for tracking pest and disease issues"""
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date_identified = db.Column(db.DateTime, default=datetime.utcnow)
    pest_type = db.Column(db.String(100))  # aphids, slugs, fungus, etc.
    severity = db.Column(db.String(20))  # mild, moderate, severe
    treatment = db.Column(db.Text)
    resolved = db.Column(db.Boolean, default=False)
    date_resolved = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'plant_id': self.plant_id,
            'date_identified': self.date_identified.isoformat() if self.date_identified else None,
            'pest_type': self.pest_type,
            'severity': self.severity,
            'treatment': self.treatment,
            'resolved': self.resolved,
            'date_resolved': self.date_resolved.isoformat() if self.date_resolved else None,
            'notes': self.notes
        }


class Task(db.Model):
    """Model for garden tasks and reminders"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_type = db.Column(db.String(50))  # watering, fertilizing, pruning, harvesting, planting
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    due_date = db.Column(db.DateTime)
    recurring = db.Column(db.Boolean, default=False)
    recurrence_interval = db.Column(db.Integer)  # days between recurrence
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.DateTime)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'task_type': self.task_type,
            'plant_id': self.plant_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'recurring': self.recurring,
            'recurrence_interval': self.recurrence_interval,
            'completed': self.completed,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WeatherLog(db.Model):
    """Model for tracking weather conditions"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    temperature_high = db.Column(db.Float)
    temperature_low = db.Column(db.Float)
    humidity = db.Column(db.Float)
    rainfall_mm = db.Column(db.Float)
    conditions = db.Column(db.String(100))  # sunny, cloudy, rainy, etc.
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'temperature_high': self.temperature_high,
            'temperature_low': self.temperature_low,
            'humidity': self.humidity,
            'rainfall_mm': self.rainfall_mm,
            'conditions': self.conditions,
            'notes': self.notes
        }


class GardenNote(db.Model):
    """Model for storing raw user notes before/after LLM processing"""
    id = db.Column(db.Integer, primary_key=True)
    raw_text = db.Column(db.Text, nullable=False)
    processed = db.Column(db.Boolean, default=False)
    extracted_data = db.Column(db.Text)  # JSON string of extracted data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'raw_text': self.raw_text,
            'processed': self.processed,
            'extracted_data': json.loads(self.extracted_data) if self.extracted_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============== API Routes ==============

# --- Plants ---
@app.route('/api/plants', methods=['GET'])
def get_plants():
    plants = Plant.query.all()
    return jsonify([plant.to_dict() for plant in plants])


@app.route('/api/plants/<int:plant_id>', methods=['GET'])
def get_plant(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    return jsonify(plant.to_dict())


@app.route('/api/plants', methods=['POST'])
def create_plant():
    data = request.json
    plant = Plant(
        name=data.get('name'),
        variety=data.get('variety'),
        location=data.get('location'),
        date_planted=datetime.fromisoformat(data['date_planted']) if data.get('date_planted') else None,
        expected_harvest=datetime.fromisoformat(data['expected_harvest']) if data.get('expected_harvest') else None,
        status=data.get('status', 'active'),
        notes=data.get('notes'),
        image_url=data.get('image_url')
    )
    db.session.add(plant)
    db.session.commit()
    return jsonify(plant.to_dict()), 201


@app.route('/api/plants/<int:plant_id>', methods=['PUT'])
def update_plant(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    data = request.json
    
    for key in ['name', 'variety', 'location', 'status', 'notes', 'image_url']:
        if key in data:
            setattr(plant, key, data[key])
    
    for key in ['date_planted', 'date_germinated', 'expected_harvest']:
        if key in data and data[key]:
            setattr(plant, key, datetime.fromisoformat(data[key]))
    
    db.session.commit()
    return jsonify(plant.to_dict())


@app.route('/api/plants/<int:plant_id>', methods=['DELETE'])
def delete_plant(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    db.session.delete(plant)
    db.session.commit()
    return '', 204


# --- Growth Logs ---
@app.route('/api/plants/<int:plant_id>/growth', methods=['GET'])
def get_growth_logs(plant_id):
    logs = GrowthLog.query.filter_by(plant_id=plant_id).order_by(GrowthLog.date.desc()).all()
    return jsonify([log.to_dict() for log in logs])


@app.route('/api/plants/<int:plant_id>/growth', methods=['POST'])
def add_growth_log(plant_id):
    Plant.query.get_or_404(plant_id)
    data = request.json
    log = GrowthLog(
        plant_id=plant_id,
        date=datetime.fromisoformat(data['date']) if data.get('date') else datetime.utcnow(),
        height_cm=data.get('height_cm'),
        width_cm=data.get('width_cm'),
        leaf_count=data.get('leaf_count'),
        health_rating=data.get('health_rating'),
        notes=data.get('notes'),
        image_url=data.get('image_url')
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(log.to_dict()), 201


# --- Watering ---
@app.route('/api/plants/<int:plant_id>/watering', methods=['POST'])
def add_watering(plant_id):
    Plant.query.get_or_404(plant_id)
    data = request.json
    watering = Watering(
        plant_id=plant_id,
        date=datetime.fromisoformat(data['date']) if data.get('date') else datetime.utcnow(),
        amount_ml=data.get('amount_ml'),
        method=data.get('method'),
        notes=data.get('notes')
    )
    db.session.add(watering)
    db.session.commit()
    return jsonify(watering.to_dict()), 201


# --- Fertilization ---
@app.route('/api/plants/<int:plant_id>/fertilization', methods=['POST'])
def add_fertilization(plant_id):
    Plant.query.get_or_404(plant_id)
    data = request.json
    fertilization = Fertilization(
        plant_id=plant_id,
        date=datetime.fromisoformat(data['date']) if data.get('date') else datetime.utcnow(),
        fertilizer_type=data.get('fertilizer_type'),
        amount=data.get('amount'),
        npk_ratio=data.get('npk_ratio'),
        notes=data.get('notes')
    )
    db.session.add(fertilization)
    db.session.commit()
    return jsonify(fertilization.to_dict()), 201


# --- Harvest ---
@app.route('/api/plants/<int:plant_id>/harvest', methods=['POST'])
def add_harvest(plant_id):
    Plant.query.get_or_404(plant_id)
    data = request.json
    harvest = Harvest(
        plant_id=plant_id,
        date=datetime.fromisoformat(data['date']) if data.get('date') else datetime.utcnow(),
        quantity=data.get('quantity'),
        unit=data.get('unit'),
        quality_rating=data.get('quality_rating'),
        notes=data.get('notes')
    )
    db.session.add(harvest)
    db.session.commit()
    return jsonify(harvest.to_dict()), 201


@app.route('/api/harvests', methods=['GET'])
def get_all_harvests():
    harvests = Harvest.query.order_by(Harvest.date.desc()).all()
    result = []
    for h in harvests:
        data = h.to_dict()
        data['plant_name'] = h.plant.name if h.plant else None
        result.append(data)
    return jsonify(result)


# --- Pest Issues ---
@app.route('/api/plants/<int:plant_id>/pests', methods=['POST'])
def add_pest_issue(plant_id):
    Plant.query.get_or_404(plant_id)
    data = request.json
    pest = PestIssue(
        plant_id=plant_id,
        pest_type=data.get('pest_type'),
        severity=data.get('severity'),
        treatment=data.get('treatment'),
        notes=data.get('notes')
    )
    db.session.add(pest)
    db.session.commit()
    return jsonify(pest.to_dict()), 201


@app.route('/api/pests/<int:pest_id>/resolve', methods=['PUT'])
def resolve_pest_issue(pest_id):
    pest = PestIssue.query.get_or_404(pest_id)
    pest.resolved = True
    pest.date_resolved = datetime.utcnow()
    db.session.commit()
    return jsonify(pest.to_dict())


@app.route('/api/pests/active', methods=['GET'])
def get_active_pests():
    pests = PestIssue.query.filter_by(resolved=False).all()
    result = []
    for p in pests:
        data = p.to_dict()
        data['plant_name'] = p.plant.name if p.plant else None
        result.append(data)
    return jsonify(result)


# --- Tasks ---
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    show_completed = request.args.get('completed', 'false').lower() == 'true'
    if show_completed:
        tasks = Task.query.all()
    else:
        tasks = Task.query.filter_by(completed=False).order_by(Task.due_date).all()
    return jsonify([task.to_dict() for task in tasks])


@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.json
    task = Task(
        title=data.get('title'),
        description=data.get('description'),
        task_type=data.get('task_type'),
        plant_id=data.get('plant_id'),
        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        recurring=data.get('recurring', False),
        recurrence_interval=data.get('recurrence_interval'),
        priority=data.get('priority', 'medium')
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@app.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.completed = True
    task.completed_date = datetime.utcnow()
    
    # If recurring, create next task
    if task.recurring and task.recurrence_interval:
        new_task = Task(
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            plant_id=task.plant_id,
            due_date=task.due_date + timedelta(days=task.recurrence_interval) if task.due_date else None,
            recurring=True,
            recurrence_interval=task.recurrence_interval,
            priority=task.priority
        )
        db.session.add(new_task)
    
    db.session.commit()
    return jsonify(task.to_dict())


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204


# --- Weather ---
@app.route('/api/weather', methods=['GET'])
def get_weather_logs():
    logs = WeatherLog.query.order_by(WeatherLog.date.desc()).limit(30).all()
    return jsonify([log.to_dict() for log in logs])


@app.route('/api/weather', methods=['POST'])
def add_weather_log():
    data = request.json
    log = WeatherLog(
        date=datetime.fromisoformat(data['date']) if data.get('date') else datetime.utcnow(),
        temperature_high=data.get('temperature_high'),
        temperature_low=data.get('temperature_low'),
        humidity=data.get('humidity'),
        rainfall_mm=data.get('rainfall_mm'),
        conditions=data.get('conditions'),
        notes=data.get('notes')
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(log.to_dict()), 201


# --- Garden Notes ---
@app.route('/api/notes', methods=['GET'])
def get_notes():
    notes = GardenNote.query.order_by(GardenNote.created_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])


@app.route('/api/notes', methods=['POST'])
def create_note():
    data = request.json
    note = GardenNote(
        raw_text=data.get('raw_text'),
        processed=data.get('processed', False),
        extracted_data=json.dumps(data.get('extracted_data')) if data.get('extracted_data') else None
    )
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    note = GardenNote.query.get_or_404(note_id)
    data = request.json
    if 'processed' in data:
        note.processed = data['processed']
    if 'extracted_data' in data:
        note.extracted_data = json.dumps(data['extracted_data'])
    db.session.commit()
    return jsonify(note.to_dict())


# --- Dashboard Stats ---
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    active_plants = Plant.query.filter_by(status='active').count()
    pending_tasks = Task.query.filter_by(completed=False).count()
    active_pests = PestIssue.query.filter_by(resolved=False).count()
    
    # Recent harvests (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_harvests = Harvest.query.filter(Harvest.date >= thirty_days_ago).count()
    
    # Tasks due soon (next 7 days)
    seven_days = datetime.utcnow() + timedelta(days=7)
    tasks_due_soon = Task.query.filter(
        Task.completed == False,
        Task.due_date <= seven_days
    ).count()
    
    return jsonify({
        'active_plants': active_plants,
        'pending_tasks': pending_tasks,
        'tasks_due_soon': tasks_due_soon,
        'active_pests': active_pests,
        'recent_harvests': recent_harvests
    })


# --- Leaderboard ---
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard data with multiple ranking metrics."""
    metric = request.args.get('metric', 'growth_rate')  # growth_rate, health, harvests
    category = request.args.get('category', 'all')
    plant_ids = request.args.get('plant_ids', '')  # Comma-separated plant IDs
    
    # Get plants
    query = Plant.query.filter_by(status='active')
    plants = query.all()
    
    # Filter by specific plant IDs if provided
    if plant_ids:
        try:
            ids = [int(id) for id in plant_ids.split(',')]
            plants = [p for p in plants if p.id in ids]
        except:
            pass
    
    # Filter by category (plant name/type)
    if category and category != 'all':
        plants = [p for p in plants if p.name.lower() == category.lower()]
    
    # Calculate metrics for each plant
    leaderboard_data = []
    for plant in plants:
        plant_data = {
            'id': plant.id,
            'name': plant.name,
            'display_name': f"{plant.name} {plant.variety or ''} #{plant.id}".strip(),
            'variety': plant.variety,
            'category': plant.name.lower(),  # Use plant name as category
        }
        
        # Calculate growth rate (cm/day)
        growth_logs = sorted(plant.growth_logs, key=lambda x: x.date)
        if len(growth_logs) >= 2:
            first_log = growth_logs[0]
            last_log = growth_logs[-1]
            days = (last_log.date - first_log.date).days or 1
            height_diff = (last_log.height_cm or 0) - (first_log.height_cm or 0)
            plant_data['growth_rate'] = round(height_diff / days, 3) if days > 0 else 0
        else:
            plant_data['growth_rate'] = 0
        
        # Calculate average health
        health_ratings = [log.health_rating for log in plant.growth_logs if log.health_rating]
        plant_data['health'] = round(sum(health_ratings) / len(health_ratings), 1) if health_ratings else 0
        
        # Count harvests
        plant_data['harvests'] = len(plant.harvests)
        
        # Get latest height
        plant_data['latest_height'] = growth_logs[-1].height_cm if growth_logs and growth_logs[-1].height_cm else 0
        
        leaderboard_data.append(plant_data)
    
    # Sort by selected metric
    leaderboard_data.sort(key=lambda x: x.get(metric, 0), reverse=True)
    
    # Assign ranks
    for i, plant in enumerate(leaderboard_data):
        plant['rank'] = i + 1
    
    # Get unique categories
    categories = list(set(p.name.lower() for p in Plant.query.filter_by(status='active').all()))
    categories.sort()
    
    return jsonify({
        'rankings': leaderboard_data,
        'leaderboard': leaderboard_data,  # Keep for backward compatibility
        'metric': metric,
        'categories': categories
    })


# --- Weather API Proxy ---
WEATHER_SETTINGS_FILE = os.path.join(basedir, 'weather_settings.json')

def load_weather_api_key():
    """Load weather API key from settings file."""
    try:
        if os.path.exists(WEATHER_SETTINGS_FILE):
            with open(WEATHER_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings.get('api_key', '')
    except:
        pass
    return ''

def save_weather_api_key(api_key):
    """Save weather API key to settings file."""
    try:
        with open(WEATHER_SETTINGS_FILE, 'w') as f:
            json.dump({'api_key': api_key}, f)
        return True
    except:
        return False

@app.route('/api/weather/search', methods=['GET'])
def search_weather():
    """Fetch current weather by zipcode or city name using OpenWeatherMap API."""
    import requests as http_requests
    
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Please provide a zipcode or city name'}), 400
    
    api_key = load_weather_api_key()
    if not api_key:
        return jsonify({
            'error': 'Weather API key not configured',
            'hint': 'Set your OpenWeatherMap API key in settings'
        }), 400
    
    # Determine if it's a zipcode (US) or city name
    if query.isdigit() and len(query) == 5:
        # US zipcode
        url = f"https://api.openweathermap.org/data/2.5/weather?zip={query},US&appid={api_key}&units=metric"
    else:
        # City name
        url = f"https://api.openweathermap.org/data/2.5/weather?q={query}&appid={api_key}&units=metric"
    
    try:
        response = http_requests.get(url, timeout=10)
        data = response.json()
        
        if response.status_code != 200:
            return jsonify({
                'error': data.get('message', 'Failed to fetch weather'),
                'code': response.status_code
            }), response.status_code
        
        # Transform the response
        weather_data = {
            'location': data.get('name', 'Unknown'),
            'country': data.get('sys', {}).get('country', ''),
            'temperature': data.get('main', {}).get('temp'),
            'temperature_high': data.get('main', {}).get('temp_max'),
            'temperature_low': data.get('main', {}).get('temp_min'),
            'feels_like': data.get('main', {}).get('feels_like'),
            'humidity': data.get('main', {}).get('humidity'),
            'pressure': data.get('main', {}).get('pressure'),
            'wind_speed': data.get('wind', {}).get('speed'),
            'conditions': data.get('weather', [{}])[0].get('description', '').title(),
            'icon': data.get('weather', [{}])[0].get('icon', ''),
            'clouds': data.get('clouds', {}).get('all'),
            'visibility': data.get('visibility'),
            'sunrise': data.get('sys', {}).get('sunrise'),
            'sunset': data.get('sys', {}).get('sunset')
        }
        
        return jsonify(weather_data)
        
    except http_requests.exceptions.Timeout:
        return jsonify({'error': 'Weather service timeout'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather/settings', methods=['GET'])
def get_weather_settings():
    """Get weather API settings (key is masked)."""
    api_key = load_weather_api_key()
    return jsonify({
        'has_api_key': bool(api_key),
        'api_key_preview': api_key[:4] + '****' + api_key[-4:] if len(api_key) > 8 else ('****' if api_key else ''),
        'service': 'OpenWeatherMap'
    })

@app.route('/api/weather/settings', methods=['POST'])
def set_weather_settings():
    """Set weather API key."""
    data = request.json
    api_key = data.get('api_key', '').strip()
    
    if not api_key:
        return jsonify({'error': 'API key is required'}), 400
    
    if save_weather_api_key(api_key):
        return jsonify({'success': True, 'message': 'API key saved'})
    else:
        return jsonify({'error': 'Failed to save API key'}), 500


# --- Initialize Database ---
def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized!")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
