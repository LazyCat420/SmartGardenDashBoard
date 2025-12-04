import sqlite3
import json

conn = sqlite3.connect('garden.db')
cursor = conn.cursor()

# Get the latest plants
plants = cursor.execute('''
    SELECT id, name, heightHistory, journalEntries 
    FROM plants 
    WHERE name LIKE "%Tomato%" OR name LIKE "%Basil%" OR name LIKE "%Pepper%"
    ORDER BY id DESC
    LIMIT 10
''').fetchall()

print('=' * 80)
print('Plant Data After Journal Processing:')
print('=' * 80)

for p in plants:
    plant_id, name, height_history, journal_entries = p
    print(f'\n🌱 {name} ({plant_id})')
    
    if height_history:
        history = json.loads(height_history)
        print(f'  📏 Height History ({len(history)} entries):')
        for h in history[-3:]:  # Show last 3
            print(f'    - {h.get("date", "N/A")}: {h.get("height")} {h.get("unit")} (source: {h.get("source", "unknown")})')
            if h.get('notes'):
                print(f'      Notes: {h.get("notes")}')
    else:
        print('  📏 Height History: None')
    
    if journal_entries:
        entries = json.loads(journal_entries)
        print(f'  📝 Journal Entries: {len(entries)} linked')
    else:
        print('  📝 Journal Entries: None')

conn.close()
print('\n' + '=' * 80)
