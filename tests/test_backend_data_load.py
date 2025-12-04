import unittest
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import database

class TestBackendDataLoad(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = 'test_data_load.db'
        database.init_db()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        if os.path.exists('test_data_load.db'):
            os.remove('test_data_load.db')

    def test_plants_and_journal_seed(self):
        # Seed data by posting plants via API (tests run against test DB)
        sample_plants = [
            { 'id': 'plant_1', 'name': 'Cherry Tomato #1', 'type': 'Tomato', 'heightHistory': [], 'feedingApplications': [], 'journalEntries': [] },
            { 'id': 'plant_2', 'name': 'Basil', 'type': 'Herb', 'heightHistory': [], 'feedingApplications': [], 'journalEntries': [] }
        ]
        for p in sample_plants:
            self.client.post('/api/plants', json=p)
        res = self.client.get('/api/plants')
        self.assertEqual(res.status_code, 200)
        plants = res.get_json()
        self.assertTrue(len(plants) >= 1)

        res2 = self.client.get('/api/journal')
        self.assertEqual(res2.status_code, 200)
        entries = res2.get_json()
        # Default to zero entries; create a journal entry and verify
        if len(entries) == 0:
            payload = { 'date': '2025-12-01', 'content': 'Seed test', 'processWithAI': False, 'processedData': { 'plants_mentioned': ['plant_1'], 'actions': [], 'summary': 'Seed' } }
            res3 = self.client.post('/api/journal', data=json.dumps(payload), content_type='application/json')
            self.assertEqual(res3.status_code, 201)
            res2 = self.client.get('/api/journal')
            entries = res2.get_json()
        self.assertTrue(len(entries) >= 1)
        # If we seeded a journal entry (optional), verify it's linked; not mandatory for this test

if __name__ == '__main__':
    unittest.main()
