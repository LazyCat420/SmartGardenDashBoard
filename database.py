import sqlite3
import json
from datetime import datetime

DB_NAME = 'garden.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Plants Table - Updated Schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            variety TEXT,
            gridId TEXT,
            quadrant TEXT,
            dateAdded TEXT,
            health TEXT,
            daysToMaturity INTEGER,
            harvestWindowStart TEXT,
            harvestWindowEnd TEXT,
            lastWatered TEXT,
            lastFed TEXT,
            notes TEXT,
            heightHistory TEXT, -- JSON string
            healthHistory TEXT, -- JSON string
            photos TEXT, -- JSON string
            feedingRecipes TEXT, -- JSON string
            feedingApplications TEXT, -- JSON string
            journalEntries TEXT -- JSON string
        )
    ''')
    
    # Migration: Add missing columns to existing plants table
    try:
        cursor.execute("PRAGMA table_info(plants)")
        columns = [info[1] for info in cursor.fetchall()]
        
        migrations = {
            'gridId': 'TEXT',
            'dateAdded': 'TEXT',
            'health': 'TEXT',
            'feedingRecipes': 'TEXT',
            'feedingApplications': 'TEXT',
            'journalEntries': 'TEXT'
        }
        
        for col, dtype in migrations.items():
            if col not in columns:
                try:
                    print(f"Migrating: Adding column {col} to plants table...")
                    cursor.execute(f"ALTER TABLE plants ADD COLUMN {col} {dtype}")
                except Exception as e:
                    print(f"Error adding column {col}: {e}")
    except Exception as e:
        print(f"Migration check failed: {e}")

    # Feeding Recipes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feeding_recipes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            feedingType TEXT,
            ingredients TEXT, -- JSON string
            schedule TEXT,
            notes TEXT,
            garden TEXT
        )
    ''')

    # Feeding Applications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feeding_applications (
            id TEXT PRIMARY KEY,
            recipeId TEXT,
            plantId TEXT,
            date TEXT,
            amount TEXT, -- JSON string {value, unit}
            appliedCost REAL,
            notes TEXT,
            FOREIGN KEY(recipeId) REFERENCES feeding_recipes(id),
            FOREIGN KEY(plantId) REFERENCES plants(id)
        )
    ''')

    # Products Table (Inventory)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT,
            category TEXT,
            purchasePrice REAL,
            packageSize TEXT, -- JSON string {amount, unit}
            costPerUnit REAL,
            purchaseDate TEXT,
            quantityPurchased REAL,
            quantityUsed REAL,
            quantityRemaining REAL,
            reorderAlert BOOLEAN
        )
    ''')

    # Journal Entries Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id TEXT PRIMARY KEY,
            date TEXT,
            content TEXT,
            tags TEXT, -- JSON string
            relatedPlantIds TEXT, -- JSON string
            processed_data TEXT, -- JSON string (processed JSON from LLM or client)
            processed BOOLEAN DEFAULT 0
        )
    ''')
    # Migration: add processed_data if missing
    try:
        cursor.execute("PRAGMA table_info(journal_entries)")
        je_cols = [info[1] for info in cursor.fetchall()]
        if 'processed_data' not in je_cols:
            print('Migrating: Adding processed_data column to journal_entries table...')
            cursor.execute('ALTER TABLE journal_entries ADD COLUMN processed_data TEXT')
    except Exception as e:
        print(f"Journal entries migration check failed: {e}")

    conn.commit()
    conn.close()
    print("Database initialized.")

if __name__ == '__main__':
    init_db()
