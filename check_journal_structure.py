import sqlite3
import json

conn = sqlite3.connect('garden.db')
cursor = conn.cursor()

entries = cursor.execute('SELECT id, date, content, tags, processed_data FROM journal_entries ORDER BY date DESC LIMIT 1').fetchall()

print('Latest Journal Entry Structure:')
print('=' * 80)
e = entries[0]
print(f'ID: {e[0]}')
print(f'Date: {e[1]}')
print(f'\nContent (first 200 chars):')
print(e[2][:200] if e[2] else 'None')
print(f'\nTags:')
print(e[3][:200] if e[3] else 'None')
print(f'\nProcessed Data:')
print(e[4][:500] if e[4] else 'None')

conn.close()
