import sqlite3
import json
import uuid
from datetime import datetime

DB_NAME = 'garden.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def seed_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if plants exist
    count = cursor.execute('SELECT COUNT(*) FROM plants').fetchone()[0]
    if count > 0:
        print(f"Database already has {count} plants. Skipping seed.")
        conn.close()
        return

    print("Seeding database with sample data...")
    
    # Sample Plants (matching index.html sample data)
    plants = [
        {
            "id": "plant_1",
            "name": "Cherry Tomato #1",
            "type": "Tomato",
            "variety": "Solanum lycopersicum var. cerasiforme",
            "gridId": "grid_1",
            "quadrant": "A1",
            "dateAdded": "2025-10-06",
            "health": "healthy",
            "heightHistory": [
                { "id": "height_1", "date": "2025-10-06", "height": 2, "unit": "cm", "source": "manual" },
                { "id": "height_13", "date": "2025-12-01", "height": 35, "unit": "cm", "source": "journal" }
            ],
            "healthHistory": [],
            "photos": [],
            "feedingRecipes": ["recipe_1"],
            "feedingApplications": ["app_1", "app_2"],
            "journalEntries": ["entry_1"]
        },
        {
            "id": "plant_2",
            "name": "Basil",
            "type": "Herb",
            "variety": "Genovese",
            "gridId": "grid_1",
            "quadrant": "A2",
            "dateAdded": "2025-10-07",
            "health": "healthy",
            "heightHistory": [
                { "date": "2025-10-07", "height": 5, "unit": "cm", "source": "manual" }
            ],
            "healthHistory": [],
            "photos": [],
            "feedingRecipes": [],
            "feedingApplications": [],
            "journalEntries": []
        }
    ]

    for p in plants:
        try:
            cursor.execute('''
                INSERT INTO plants (id, name, type, variety, gridId, quadrant, dateAdded, health, 
                                    heightHistory, healthHistory, photos, feedingRecipes, 
                                    feedingApplications, journalEntries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p['id'], p['name'], p['type'], p.get('variety'), p['gridId'], p['quadrant'], 
                p['dateAdded'], p['health'],
                json.dumps(p['heightHistory']),
                json.dumps(p['healthHistory']),
                json.dumps(p['photos']),
                json.dumps(p['feedingRecipes']),
                json.dumps(p['feedingApplications']),
                json.dumps(p['journalEntries'])
            ))
            print(f"Added plant: {p['name']}")
        except Exception as e:
            print(f"Error adding plant {p['name']}: {e}")
            # If column missing (schema mismatch), we might fail here. 
            # But we are about to fix schema too.

    conn.commit()
    # Seed a sample journal entry 'entry_1' if not exists
    try:
        cursor.execute("SELECT COUNT(*) FROM journal_entries WHERE id = 'entry_1'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO journal_entries (id, date, content, tags, relatedPlantIds, processed_data, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'entry_1', '2025-12-01', 'Journal seeded: Tomato reached 35cm', json.dumps([]), json.dumps(['plant_1']), json.dumps({ 'plants_mentioned': ['Cherry Tomato #1'], 'actions': [ { 'action_type': 'height_measurement', 'plant': 'Cherry Tomato #1', 'height': 35, 'unit': 'cm'} ], 'summary': 'Tomato reached 35cm' }), True
            ))
            print('Seeded journal entry: entry_1')
    except Exception as e:
        print(f"Error seeding journal entry: {e}")
    conn.close()
    print("Seeding complete.")

if __name__ == '__main__':
    seed_data()
