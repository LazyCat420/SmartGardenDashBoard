import unittest
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import database
from unittest.mock import patch

class TestJournalAPI(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Use a temporary DB
        self.original_db_name = database.DB_NAME
        database.DB_NAME = 'test_journal.db'
        database.init_db()

        # Create a plant for mapping
        self.plant = {
            'id': 'plant-tomato',
            'name': 'Tomato',
            'type': 'Vegetable',
            'heightHistory': []
        }
        self.client.post('/api/plants', json=self.plant)

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        if os.path.exists('test_journal.db'):
            os.remove('test_journal.db')

    def test_post_raw_journal(self):
        data = {'date': '2025-12-03', 'content': 'Watered the bed.'}
        res = self.client.post('/api/journal', data=json.dumps(data), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertEqual(res_json['content'], 'Watered the bed.')
        # GET entries
        res2 = self.client.get('/api/journal')
        self.assertEqual(res2.status_code, 200)
        entries = res2.get_json()
        self.assertTrue(len(entries) >= 1)

    def test_post_processed_journal_updates_plant(self):
        processed_data = {
            'plants_mentioned': ['Tomato'],
            'actions': [
                { 'action_type': 'height_measurement', 'plant': 'Tomato', 'height': 45, 'unit': 'cm' }
            ],
            'summary': 'Tomato grew.'
        }
        data = {
            'date': '2025-12-03',
            'content': 'Tomato now 45cm tall',
            'processWithAI': True,
            'processedData': processed_data
        }
        res = self.client.post('/api/journal', data=json.dumps(data), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertIn('relatedPlantIds', res_json)
        self.assertIn('plant-tomato', res_json['relatedPlantIds'])
        # Check plants
        res_plants = self.client.get('/api/plants')
        plants = res_plants.get_json()
        plant = [p for p in plants if p['id'] == 'plant-tomato'][0]
        self.assertTrue(len(plant['heightHistory']) >= 1)
        self.assertEqual(plant['heightHistory'][-1]['height'], 45)
        self.assertEqual(plant['heightHistory'][-1]['source'], 'journal_ai')
        # Ensure journal entry ID in plant's journalEntries
        res_journal = self.client.get('/api/journal')
        entries = res_journal.get_json()
        new_id = res_json['id']
        self.assertIn(new_id, plant['journalEntries'])
        # GET /api/journal returns processed data in tags
        res2 = self.client.get('/api/journal')
        entries = res2.get_json()
        created = next((e for e in entries if e['id'] == new_id), None)
        self.assertIsNotNone(created)
        self.assertTrue(created['processed'])
        self.assertIsInstance(created['tags'], dict)

    @patch('llm_service.process_journal_entry')
    def test_post_journal_with_llm_service(self, mock_llm):
        # Mock LLM response
        mock_llm.return_value = {
            'success': True,
            'processed_data': {
                'plants_mentioned': ['Tomato'],
                'actions': [
                    {'action_type': 'height_measurement', 'plant': 'Tomato', 'height': 50, 'unit': 'cm'}
                ],
                'summary': 'Tomato growth'
            }
        }
        data = {
            'date': '2025-12-04',
            'content': 'Tomato is now 50cm tall',
            'processWithAI': True
        }
        res = self.client.post('/api/journal', data=json.dumps(data), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertTrue(mock_llm.called)
        self.assertIn('plant-tomato', res_json['relatedPlantIds'])
        # Verify plant updated
        res_plants = self.client.get('/api/plants')
        plant = [p for p in res_plants.get_json() if p['id'] == 'plant-tomato'][0]
        self.assertEqual(plant['heightHistory'][-1]['height'], 50)

    def test_post_processed_journal_feeding_updates_plant(self):
        processed_data = {
            'plants_mentioned': ['Tomato'],
            'actions': [
                {'action_type': 'feeding', 'plant': 'Tomato', 'details': 'Compost Tea', 'amount': 5}
            ],
            'summary': 'Fed Tomato with Compost Tea'
        }
        data = {
            'date': '2025-12-03',
            'content': 'Applied compost to tomato',
            'processWithAI': True,
            'processedData': processed_data
        }
        res = self.client.post('/api/journal', data=json.dumps(data), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        res_json = res.get_json()
        self.assertIn('plant-tomato', res_json['relatedPlantIds'])
        res_plants = self.client.get('/api/plants')
        plant = [p for p in res_plants.get_json() if p['id'] == 'plant-tomato'][0]
        self.assertTrue(len(plant['feedingApplications']) >= 1)
        app_id = plant['feedingApplications'][-1]
        # Lookup application
        res_apps = self.client.get('/api/applications')
        apps = res_apps.get_json()
        found_app = next((a for a in apps if a['id'] == app_id), None)
        self.assertIsNotNone(found_app)
        self.assertEqual(found_app['notes'], 'AI Logged: Compost Tea')

if __name__ == '__main__':
    unittest.main()
