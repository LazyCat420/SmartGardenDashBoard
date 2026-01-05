
"""
Tests for Task API endpoints
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_md import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

class TestTasksEndpoint:
    """Tests for Task endpoints"""
    
    def test_create_and_update_task(self, client):
        """Test task creation and update/toggle"""
        
        # 1. Create Task
        task_data = {
            "title": "Test Update Task",
            "priority": "high",
            "due_date": "2025-01-01"
        }
        response = client.post('/api/tasks', json=task_data)
        assert response.status_code == 201
        task = json.loads(response.data)
        task_id = task['id']
        assert task['title'] == "Test Update Task"
        assert not task.get('completed')
        
        # 2. Update Task (Toggle Complete)
        update_data = {"completed": True}
        response = client.put(f'/api/tasks/{task_id}', json=update_data)
        assert response.status_code == 200
        updated_task = json.loads(response.data)
        assert updated_task['completed'] is True
        assert updated_task.get('completed_date') is not None
        
        # 3. Update Task (Toggle Uncomplete)
        update_data = {"completed": False}
        response = client.put(f'/api/tasks/{task_id}', json=update_data)
        assert response.status_code == 200
        uncompleted_task = json.loads(response.data)
        assert uncompleted_task['completed'] is False
        assert uncompleted_task.get('completed_date') is None
        
        # 4. Clean up
        response = client.delete(f'/api/tasks/{task_id}')
        assert response.status_code == 200

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
