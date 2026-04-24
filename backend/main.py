"""
Main entry point for Smart Garden Dashboard Backend
"""

from flask import Flask, request, jsonify, send_file, redirect
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import os
import requests
import qrcode
from qrcode.constants import ERROR_CORRECT_L
import io
import base64
import uuid

app = Flask(__name__, static_folder='../frontend', static_url_path='')
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
    instance_number = db.Column(db.Integer, default=1)  # For multiple plants: #1, #2, etc.
    unique_code = db.Column(db.String(12), unique=True)  # Short code for QR: e.g., "TOM-001"
    location = db.Column(db.String(100))
    date_planted = db.Column(db.DateTime)
    date_germinated = db.Column(db.DateTime)
    expected_harvest = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='active')
    notes = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    growth_logs = db.relationship('GrowthLog', backref='plant', lazy=True, cascade='all, delete-orphan')
    waterings = db.relationship('Watering', backref='plant', lazy=True, cascade='all, delete-orphan')
    fertilizations = db.relationship('Fertilization', backref='plant', lazy=True, cascade='all, delete-orphan')
    harvests = db.relationship('Harvest', backref='plant', lazy=True, cascade='all, delete-orphan')
    pest_issues = db.relationship('PestIssue', backref='plant', lazy=True, cascade='all, delete-orphan')

    @property
    def display_name(self):
        """Returns name with instance number if there are multiple"""
        if self.instance_number and self.instance_number > 0:
            return f"{self.name} #{self.instance_number}"
        return self.name
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'variety': self.variety,
            'instance_number': self.instance_number,
            'unique_code': self.unique_code,
            'display_name': self.display_name,
            'location': self.location,
            'date_planted': self.date_planted.isoformat() if self.date_planted else None,
            'date_germinated': self.date_germinated.isoformat() if self.date_germinated else None,
            'expected_harvest': self.expected_harvest.isoformat() if self.expected_harvest else None,
            'status': self.status,
            'notes': self.notes,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'growth_logs': [log.to_dict() for log in self.growth_logs],
            'waterings': [w.to_dict() for w in self.waterings[-5:]],
            'fertilizations': [f.to_dict() for f in self.fertilizations[-5:]],
            'harvests': [h.to_dict() for h in self.harvests],
            'pest_issues': [p.to_dict() for p in self.pest_issues]
        }


class GrowthLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    height_cm = db.Column(db.Float)
    width_cm = db.Column(db.Float)
    leaf_count = db.Column(db.Integer)
    health_rating = db.Column(db.Integer)
    notes = db.Column(db.Text)
    image_url = db.Column(db.String(500))

    def to_dict(self):
        return {
            'id': self.id, 'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'height_cm': self.height_cm, 'width_cm': self.width_cm,
            'leaf_count': self.leaf_count, 'health_rating': self.health_rating,
            'notes': self.notes, 'image_url': self.image_url
        }


class Watering(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    amount_ml = db.Column(db.Float)
    method = db.Column(db.String(50))
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'amount_ml': self.amount_ml, 'method': self.method, 'notes': self.notes
        }


class Fertilization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    fertilizer_type = db.Column(db.String(100))
    amount = db.Column(db.String(50))
    npk_ratio = db.Column(db.String(20))
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'fertilizer_type': self.fertilizer_type, 'amount': self.amount,
            'npk_ratio': self.npk_ratio, 'notes': self.notes
        }


class Harvest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20))
    quality_rating = db.Column(db.Integer)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'plant_id': self.plant_id,
            'date': self.date.isoformat() if self.date else None,
            'quantity': self.quantity, 'unit': self.unit,
            'quality_rating': self.quality_rating, 'notes': self.notes
        }


class PestIssue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)
    date_identified = db.Column(db.DateTime, default=datetime.utcnow)
    pest_type = db.Column(db.String(100))
    severity = db.Column(db.String(20))
    treatment = db.Column(db.Text)
    resolved = db.Column(db.Boolean, default=False)
    date_resolved = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'plant_id': self.plant_id,
            'date_identified': self.date_identified.isoformat() if self.date_identified else None,
            'pest_type': self.pest_type, 'severity': self.severity,
            'treatment': self.treatment, 'resolved': self.resolved,
            'date_resolved': self.date_resolved.isoformat() if self.date_resolved else None,
            'notes': self.notes
        }


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_type = db.Column(db.String(50))
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'))
    due_date = db.Column(db.DateTime)
    recurring = db.Column(db.Boolean, default=False)
    recurrence_interval = db.Column(db.Integer)
    completed = db.Column(db.Boolean, default=False)
    completed_date = db.Column(db.DateTime)
    priority = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'description': self.description,
            'task_type': self.task_type, 'plant_id': self.plant_id,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'recurring': self.recurring, 'recurrence_interval': self.recurrence_interval,
            'completed': self.completed,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WeatherLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    temperature_high = db.Column(db.Float)
    temperature_low = db.Column(db.Float)
    humidity = db.Column(db.Float)
    rainfall_mm = db.Column(db.Float)
    conditions = db.Column(db.String(100))
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'date': self.date.isoformat() if self.date else None,
            'temperature_high': self.temperature_high, 'temperature_low': self.temperature_low,
            'humidity': self.humidity, 'rainfall_mm': self.rainfall_mm,
            'conditions': self.conditions, 'notes': self.notes
        }


class GardenNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    raw_text = db.Column(db.Text, nullable=False)
    processed = db.Column(db.Boolean, default=False)
    extracted_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'raw_text': self.raw_text, 'processed': self.processed,
            'extracted_data': json.loads(self.extracted_data) if self.extracted_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============== LLM Service ==============

LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "ibm-granite/granite-3.3-8b-instruct"

# Try to load settings from file
# Try to load settings from file - REVERTED
# try:
#     settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')
#     if os.path.exists(settings_file):
#         with open(settings_file, 'r') as f:
#             settings = json.load(f)
#             LMSTUDIO_URL = settings.get("url", LMSTUDIO_URL)
#             MODEL_NAME = settings.get("model", MODEL_NAME)
#             print(f"Loaded LLM settings: URL={LMSTUDIO_URL}, Model={MODEL_NAME}")
# except Exception as e:
#     print(f"Error loading LLM settings: {e}")

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
                    "notes": {"type": "string", "description": "Additional notes"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_watering",
            "description": "Log a watering event for a plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "amount_ml": {"type": "number", "description": "Amount in ml"},
                    "method": {"type": "string", "description": "Watering method"},
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
            "description": "Log a fertilization event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "fertilizer_type": {"type": "string", "description": "Type of fertilizer"},
                    "amount": {"type": "string", "description": "Amount applied"},
                    "npk_ratio": {"type": "string", "description": "NPK ratio"},
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
            "name": "log_harvest",
            "description": "Log a harvest event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "quantity": {"type": "number", "description": "Amount harvested"},
                    "unit": {"type": "string", "description": "Unit (kg, lbs, pieces)"},
                    "quality_rating": {"type": "integer", "description": "Quality 1-10"},
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
            "description": "Report a pest or disease issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Affected plant"},
                    "pest_type": {"type": "string", "description": "Type of pest/disease"},
                    "severity": {"type": "string", "enum": ["mild", "moderate", "severe"]},
                    "treatment": {"type": "string", "description": "Treatment applied"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
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
                    "description": {"type": "string", "description": "Task description"},
                    "task_type": {"type": "string", "enum": ["watering", "fertilizing", "pruning", "harvesting", "planting", "pest_control", "maintenance", "other"]},
                    "plant_name": {"type": "string", "description": "Related plant"},
                    "due_date": {"type": "string", "description": "Due date (YYYY-MM-DD)"},
                    "recurring": {"type": "boolean", "description": "Is recurring?"},
                    "recurrence_interval": {"type": "integer", "description": "Days between recurrence"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]}
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
                    "temperature_high": {"type": "number", "description": "High temp (°C)"},
                    "temperature_low": {"type": "number", "description": "Low temp (°C)"},
                    "humidity": {"type": "number", "description": "Humidity %"},
                    "rainfall_mm": {"type": "number", "description": "Rainfall mm"},
                    "conditions": {"type": "string", "description": "Weather conditions"},
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
            "description": "Update the status of an existing plant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "plant_name": {"type": "string", "description": "Plant name"},
                    "status": {"type": "string", "enum": ["active", "harvested", "removed", "dormant"]},
                    "notes": {"type": "string", "description": "Notes"}
                },
                "required": ["plant_name", "status"]
            }
        }
    }
]

SYSTEM_PROMPT = """You are a smart garden assistant that extracts structured data from natural language notes.

Your job is to:
1. Read the user's note about their garden
2. Identify ALL relevant garden activities mentioned
3. Call the appropriate function(s) to log each piece of information
4. Extract as much detail as possible

Guidelines:
- Use current date ({current_date}) for "today"
- Convert measurements to metric when possible
- Make separate function calls for each plant/activity
- For health: "great/excellent" = 8-10, "okay/fine" = 5-7, "poor/bad" = 3-4, "dying" = 1-2

Current date: {current_date}
Existing plants: {plant_list}

Extract all information and make appropriate function calls."""


def parse_date(date_str):
    if not date_str:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(date_str)
    except:
        return datetime.utcnow()


def find_or_create_plant(name):
    plant = Plant.query.filter(Plant.name.ilike(f"%{name}%")).first()
    if not plant:
        plant = Plant(name=name, status='active')
        db.session.add(plant)
        db.session.flush()
    return plant


def apply_action(action_type, params):
    """Apply a single extracted action to the database."""
    if action_type == "add_plant":
        plant = Plant(
            name=params.get('name'),
            variety=params.get('variety'),
            location=params.get('location'),
            date_planted=parse_date(params.get('date_planted')),
            notes=params.get('notes'),
            status='active'
        )
        db.session.add(plant)
        return {"action": action_type, "success": True, "message": f"Added plant: {params.get('name')}"}
    
    elif action_type == "log_watering":
        plant = find_or_create_plant(params.get('plant_name'))
        watering = Watering(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            amount_ml=params.get('amount_ml'),
            method=params.get('method'),
            notes=params.get('notes')
        )
        db.session.add(watering)
        return {"action": action_type, "success": True, "message": f"Logged watering for: {params.get('plant_name')}"}
    
    elif action_type == "log_fertilization":
        plant = find_or_create_plant(params.get('plant_name'))
        fert = Fertilization(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            fertilizer_type=params.get('fertilizer_type'),
            amount=params.get('amount'),
            npk_ratio=params.get('npk_ratio'),
            notes=params.get('notes')
        )
        db.session.add(fert)
        return {"action": action_type, "success": True, "message": f"Logged fertilization for: {params.get('plant_name')}"}
    
    elif action_type == "log_harvest":
        plant = find_or_create_plant(params.get('plant_name'))
        harvest = Harvest(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            quantity=params.get('quantity'),
            unit=params.get('unit'),
            quality_rating=params.get('quality_rating'),
            notes=params.get('notes')
        )
        db.session.add(harvest)
        return {"action": action_type, "success": True, "message": f"Logged harvest for: {params.get('plant_name')}"}
    
    elif action_type == "log_growth":
        plant = find_or_create_plant(params.get('plant_name'))
        growth = GrowthLog(
            plant_id=plant.id,
            date=parse_date(params.get('date')),
            height_cm=params.get('height_cm'),
            width_cm=params.get('width_cm'),
            leaf_count=params.get('leaf_count'),
            health_rating=params.get('health_rating'),
            notes=params.get('notes')
        )
        db.session.add(growth)
        return {"action": action_type, "success": True, "message": f"Logged growth for: {params.get('plant_name')}"}
    
    elif action_type == "report_pest_issue":
        plant = find_or_create_plant(params.get('plant_name'))
        pest = PestIssue(
            plant_id=plant.id,
            date_identified=parse_date(params.get('date')),
            pest_type=params.get('pest_type'),
            severity=params.get('severity', 'moderate'),
            treatment=params.get('treatment'),
            notes=params.get('notes')
        )
        db.session.add(pest)
        return {"action": action_type, "success": True, "message": f"Reported pest issue for: {params.get('plant_name')}"}
    
    elif action_type == "create_task":
        plant = None
        if params.get('plant_name'):
            plant = Plant.query.filter(Plant.name.ilike(f"%{params.get('plant_name')}%")).first()
        task = Task(
            title=params.get('title'),
            description=params.get('description'),
            task_type=params.get('task_type', 'other'),
            plant_id=plant.id if plant else None,
            due_date=parse_date(params.get('due_date')),
            recurring=params.get('recurring', False),
            recurrence_interval=params.get('recurrence_interval'),
            priority=params.get('priority', 'medium')
        )
        db.session.add(task)
        return {"action": action_type, "success": True, "message": f"Created task: {params.get('title')}"}
    
    elif action_type == "log_weather":
        weather = WeatherLog(
            date=parse_date(params.get('date')),
            temperature_high=params.get('temperature_high'),
            temperature_low=params.get('temperature_low'),
            humidity=params.get('humidity'),
            rainfall_mm=params.get('rainfall_mm'),
            conditions=params.get('conditions'),
            notes=params.get('notes')
        )
        db.session.add(weather)
        return {"action": action_type, "success": True, "message": "Logged weather conditions"}
    
    elif action_type == "update_plant_status":
        plant = Plant.query.filter(Plant.name.ilike(f"%{params.get('plant_name')}%")).first()
        if plant:
            plant.status = params.get('status', 'active')
            if params.get('notes'):
                plant.notes = (plant.notes or '') + '\n' + params.get('notes')
            return {"action": action_type, "success": True, "message": f"Updated status for: {params.get('plant_name')}"}
        return {"action": action_type, "success": False, "message": f"Plant not found: {params.get('plant_name')}"}
    
    return {"action": action_type, "success": False, "message": f"Unknown action: {action_type}"}


# ============== API Routes ==============

@app.route('/')
def index():
    return app.send_static_file('index.html')


# --- Plants ---
@app.route('/api/plants', methods=['GET'])
def get_plants():
    plants = Plant.query.all()
    return jsonify([plant.to_dict() for plant in plants])


@app.route('/api/plants/<int:plant_id>', methods=['GET'])
def get_plant(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    return jsonify(plant.to_dict())


def generate_unique_code(name, instance_num):
    """Generate a short unique code for QR: e.g., TOM-001"""
    # Take first 3 letters of name (uppercase)
    prefix = ''.join(c for c in name.upper() if c.isalpha())[:3]
    if len(prefix) < 3:
        prefix = prefix.ljust(3, 'X')
    return f"{prefix}-{instance_num:03d}"


def get_next_instance_number(name, variety=None):
    """Get the next instance number for a plant type"""
    query = Plant.query.filter(Plant.name.ilike(name))
    if variety:
        query = query.filter(Plant.variety.ilike(variety))
    max_instance = db.session.query(db.func.max(Plant.instance_number)).filter(
        Plant.name.ilike(name)
    ).scalar()
    return (max_instance or 0) + 1


@app.route('/api/plants', methods=['POST'])
def create_plant():
    data = request.json
    quantity = data.get('quantity', 1)
    created_plants = []
    
    for i in range(quantity):
        instance_num = get_next_instance_number(data.get('name'), data.get('variety'))
        unique_code = generate_unique_code(data.get('name'), instance_num)
        
        # Ensure unique code is actually unique
        while Plant.query.filter_by(unique_code=unique_code).first():
            instance_num += 1
            unique_code = generate_unique_code(data.get('name'), instance_num)
        
        plant = Plant(
            name=data.get('name'),
            variety=data.get('variety'),
            instance_number=instance_num,
            unique_code=unique_code,
            location=data.get('location'),
            date_planted=datetime.fromisoformat(data['date_planted']) if data.get('date_planted') else None,
            expected_harvest=datetime.fromisoformat(data['expected_harvest']) if data.get('expected_harvest') else None,
            status=data.get('status', 'active'),
            notes=data.get('notes'),
            image_url=data.get('image_url')
        )
        db.session.add(plant)
        db.session.flush()  # Get the ID
        created_plants.append(plant)
    
    db.session.commit()
    
    if quantity == 1:
        return jsonify(created_plants[0].to_dict()), 201
    return jsonify([p.to_dict() for p in created_plants]), 201


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


# --- QR Code & Label Generation ---
@app.route('/api/plants/<int:plant_id>/qr', methods=['GET'])
def get_plant_qr(plant_id):
    """Generate QR code for a plant - optimized for 12x40mm stickers"""
    plant = Plant.query.get_or_404(plant_id)
    
    # Create QR code with minimal size for micro labels
    qr = qrcode.QRCode(
        version=1,  # Smallest version
        error_correction=ERROR_CORRECT_L,  # Low error correction = smaller
        box_size=3,  # Small pixels
        border=1,  # Minimal border
    )
    
    # QR data: just the unique code (short for small QR)
    qr.add_data(plant.unique_code)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to bytes
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png')


@app.route('/api/plants/<int:plant_id>/label', methods=['GET'])
def get_plant_label(plant_id):
    """Generate a printable label image for 12x40mm stickers (at 300 DPI)"""
    from PIL import Image, ImageDraw, ImageFont
    
    plant = Plant.query.get_or_404(plant_id)
    
    # 12x40mm at 300 DPI = 142 x 472 pixels
    # But we'll make it slightly smaller for margins: 130 x 450
    label_width = 450
    label_height = 130
    
    # Create white background
    label = Image.new('RGB', (label_width, label_height), 'white')
    draw = ImageDraw.Draw(label)
    
    # Generate QR code with URL that opens the plant directly
    # The URL will redirect to the app with the plant selected
    qr_url = f"{request.host_url}plant/{plant.unique_code}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_L,
        box_size=4,
        border=1,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize QR to fit height
    qr_size = label_height - 10  # 120px
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)
    
    # Paste QR on left side
    label.paste(qr_img, (5, 5))
    
    # Add text on right side
    text_x = qr_size + 15
    
    # Try to use a system font, fallback to default
    try:
        # Try common fonts
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
    
    # Plant name (truncate if too long)
    display_name = plant.display_name
    if len(display_name) > 15:
        display_name = display_name[:14] + "…"
    
    draw.text((text_x, 10), display_name, fill='black', font=font_large)
    
    # Variety (if exists)
    if plant.variety:
        variety_text = plant.variety[:20] + "…" if len(plant.variety) > 20 else plant.variety
        draw.text((text_x, 45), variety_text, fill='gray', font=font_medium)
    
    # Unique code
    draw.text((text_x, 75), plant.unique_code, fill='black', font=font_medium)
    
    # Location (if exists)
    if plant.location:
        loc_text = plant.location[:18] + "…" if len(plant.location) > 18 else plant.location
        draw.text((text_x, 100), f"📍 {loc_text}", fill='gray', font=font_small)
    
    # Save to bytes
    img_buffer = io.BytesIO()
    label.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, mimetype='image/png')


@app.route('/api/plants/<int:plant_id>/label-data', methods=['GET'])
def get_plant_label_data(plant_id):
    """Get label data as base64 for frontend display"""
    from PIL import Image, ImageDraw, ImageFont
    
    plant = Plant.query.get_or_404(plant_id)
    
    # 12x40mm at 300 DPI = 142 x 472 pixels
    label_width = 450
    label_height = 130
    
    # Create white background
    label = Image.new('RGB', (label_width, label_height), 'white')
    draw = ImageDraw.Draw(label)
    
    # Generate QR code with URL that opens the plant directly
    qr_url = f"{request.host_url}plant/{plant.unique_code}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_L,
        box_size=4,
        border=1,
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize QR to fit height
    qr_size = label_height - 10
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.NEAREST)
    
    # Paste QR on left side
    label.paste(qr_img, (5, 5))
    
    # Add text on right side
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
    
    display_name = plant.display_name
    if len(display_name) > 15:
        display_name = display_name[:14] + "…"
    
    draw.text((text_x, 10), display_name, fill='black', font=font_large)
    
    if plant.variety:
        variety_text = plant.variety[:20] + "…" if len(plant.variety) > 20 else plant.variety
        draw.text((text_x, 45), variety_text, fill='gray', font=font_medium)
    
    draw.text((text_x, 75), plant.unique_code, fill='black', font=font_medium)
    
    if plant.location:
        loc_text = plant.location[:18] + "…" if len(plant.location) > 18 else plant.location
        draw.text((text_x, 100), loc_text, fill='gray', font=font_small)
    
    # Convert to base64
    img_buffer = io.BytesIO()
    label.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    base64_img = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    
    return jsonify({
        'plant_id': plant.id,
        'display_name': plant.display_name,
        'unique_code': plant.unique_code,
        'label_image': f"data:image/png;base64,{base64_img}"
    })


@app.route('/api/plants/batch-labels', methods=['POST'])
def get_batch_labels():
    """Generate labels for multiple plants"""
    data = request.json
    plant_ids = data.get('plant_ids', [])
    
    labels = []
    for plant_id in plant_ids:
        plant = Plant.query.get(plant_id)
        if plant:
            # Get label data
            response = get_plant_label_data(plant_id)
            labels.append(response.get_json())
    
    return jsonify(labels)


@app.route('/api/plants/by-code/<code>', methods=['GET'])
def get_plant_by_code(code):
    """Look up a plant by its unique QR code"""
    plant = Plant.query.filter_by(unique_code=code.upper()).first()
    if not plant:
        return jsonify({'error': 'Plant not found'}), 404
    return jsonify(plant.to_dict())


@app.route('/plant/<code>')
def plant_qr_redirect(code):
    """Redirect from QR code scan to the dashboard with plant selected.
    This allows users to scan a QR code and be taken directly to that plant."""
    plant = Plant.query.filter_by(unique_code=code.upper()).first()
    if not plant:
        # Redirect to home if plant not found
        return redirect('/?error=plant_not_found')
    # Redirect to the app with the plant ID as a URL parameter
    return redirect(f'/?plant={plant.id}&action=view')


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
    fert = Fertilization(
        plant_id=plant_id,
        date=datetime.fromisoformat(data['date']) if data.get('date') else datetime.utcnow(),
        fertilizer_type=data.get('fertilizer_type'),
        amount=data.get('amount'),
        npk_ratio=data.get('npk_ratio'),
        notes=data.get('notes')
    )
    db.session.add(fert)
    db.session.commit()
    return jsonify(fert.to_dict()), 201


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


# --- Dashboard Stats ---
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    active_plants = Plant.query.filter_by(status='active').count()
    pending_tasks = Task.query.filter_by(completed=False).count()
    active_pests = PestIssue.query.filter_by(resolved=False).count()
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_harvests = Harvest.query.filter(Harvest.date >= thirty_days_ago).count()
    seven_days = datetime.utcnow() + timedelta(days=7)
    tasks_due_soon = Task.query.filter(Task.completed == False, Task.due_date <= seven_days).count()
    return jsonify({
        'active_plants': active_plants,
        'pending_tasks': pending_tasks,
        'tasks_due_soon': tasks_due_soon,
        'active_pests': active_pests,
        'recent_harvests': recent_harvests
    })


# --- LLM Routes ---
@app.route('/api/llm/status', methods=['GET'])
def llm_status():
    try:
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')
        api_key = ""
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                api_key = settings.get("api_key", "")
                
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        response = requests.post(
            LMSTUDIO_URL,
            headers=headers,
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=10
        )
        response.raise_for_status()
        return jsonify({"connected": True, "message": "LMStudio is connected"})
    except:
        return jsonify({"connected": False, "message": "Cannot connect to LMStudio"})


@app.route('/api/llm/settings', methods=['GET'])
def get_llm_settings():
    """Get current LLM settings."""
    try:
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        else:
            settings = {
                "url": "http://localhost:1234/v1/chat/completions",
                "model": "ibm-granite/granite-3.3-8b-instruct",
                "api_key": "",
                "endpoint_type": "lmstudio",
                "context_length": 8192,
                "gpu_layers": 35,
                "cpu_threads": 8
            }
        
        return jsonify({
            **settings,
            "defaults": {
                "url": "http://localhost:1234/v1/chat/completions",
                "model": "ibm-granite/granite-3.3-8b-instruct",
                "api_key": "",
                "endpoint_type": "lmstudio",
                "context_length": 8192,
                "gpu_layers": 35,
                "cpu_threads": 8
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/llm/settings', methods=['POST'])
def save_llm_settings():
    """Save LLM settings."""
    try:
        data = request.json
        settings = {
            "url": data.get("url", "http://localhost:1234/v1/chat/completions"),
            "model": data.get("model", "ibm-granite/granite-3.3-8b-instruct"),
            "api_key": data.get("api_key", ""),
            "endpoint_type": data.get("endpoint_type", "lmstudio"),
            "context_length": data.get("context_length", 8192),
            "gpu_layers": data.get("gpu_layers", 35),
            "cpu_threads": data.get("cpu_threads", 8)
        }
        
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Reload global settings
        global LMSTUDIO_URL, MODEL_NAME
        LMSTUDIO_URL = settings["url"]
        MODEL_NAME = settings["model"]
        
        return jsonify({"success": True, "message": "Settings saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/llm/models', methods=['GET'])
def get_llm_models():
    """Get available models from LMStudio."""
    try:
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                base_url = settings.get("url", "http://localhost:1234/v1/chat/completions")
        else:
            base_url = "http://localhost:1234/v1/chat/completions"
        
        # Extract the base URL for the models endpoint
        models_url = base_url.replace("/v1/chat/completions", "/v1/models")
        
        response = requests.get(models_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Extract model IDs from the response
        models = []
        if "data" in data:
            models = [model.get("id") for model in data["data"] if model.get("id")]
        
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})


@app.route('/api/llm/process-note', methods=['POST'])
def process_note():
    data = request.json
    note_text = data.get('note', '')
    
    if not note_text:
        return jsonify({"error": "No note text provided"}), 400
    
    plants = Plant.query.filter_by(status='active').all()
    plant_names = [p.name for p in plants]
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_message = SYSTEM_PROMPT.format(
        current_date=current_date,
        plant_list=", ".join(plant_names) if plant_names else "No plants yet"
    )
    
    try:
        settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llm_settings.json')
        api_key = ""
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                api_key = settings.get("api_key", "")
                
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        response = requests.post(
            LMSTUDIO_URL,
            headers=headers,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": note_text}
                ],
                "tools": GARDEN_TOOLS,
                "tool_choice": "auto",
                "temperature": 0.3,
                "max_tokens": 2000
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        
        # Extract tool calls
        extracted_actions = []
        message = result.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls", [])
        
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            args = func.get("arguments", "{}")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except:
                    args = {}
            extracted_actions.append({
                "action": func.get("name"),
                "parameters": args
            })
        
        # Save the note
        note = GardenNote(
            raw_text=note_text,
            processed=True,
            extracted_data=json.dumps(extracted_actions)
        )
        db.session.add(note)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "note_id": note.id,
            "raw_note": note_text,
            "extracted_actions": extracted_actions,
            "assistant_message": message.get("content", "")
        })
        
    except requests.exceptions.ConnectionError:
        return jsonify({
            "success": False,
            "error": "Could not connect to LMStudio. Make sure it's running on localhost:1234"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/llm/apply-actions', methods=['POST'])
def apply_actions():
    data = request.json
    actions = data.get('actions', [])
    results = []
    
    for action in actions:
        try:
            result = apply_action(action.get('action'), action.get('parameters', {}))
            results.append(result)
        except Exception as e:
            results.append({"action": action.get('action'), "success": False, "error": str(e)})
    
    db.session.commit()
    return jsonify({"results": results})


# Initialize database
def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized!")


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
