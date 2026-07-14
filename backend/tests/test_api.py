"""
Tests for Smart Garden Dashboard API endpoints
Tests for LLM model dropdown and Leaderboard functionality
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_md import app


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestLLMModelsEndpoint:
    """Tests for the /api/llm/models endpoint"""
    
    @patch('main_md.requests.get')
    def test_models_openai_format_parsing(self, mock_get, client):
        """Test that OpenAI-style response format is parsed correctly"""
        # Mock LMStudio returning OpenAI-compatible format
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {"id": "llama-3.2-1b-instruct", "object": "model"},
                {"id": "qwen2.5-3b-instruct", "object": "model"},
                {"id": "granite-3.3-8b-instruct", "object": "model"}
            ]
        }
        mock_get.return_value = mock_response
        
        response = client.get('/api/llm/models')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'models' in data
        assert len(data['models']) == 3
        assert 'llama-3.2-1b-instruct' in data['models']
        assert 'qwen2.5-3b-instruct' in data['models']
        assert 'granite-3.3-8b-instruct' in data['models']
    
    @patch('main_md.requests.get')
    def test_models_list_format_parsing(self, mock_get, client):
        """Test that list of model objects is parsed correctly"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "model-1"},
            {"id": "model-2"}
        ]
        mock_get.return_value = mock_response
        
        response = client.get('/api/llm/models')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'models' in data
        assert 'model-1' in data['models']
        assert 'model-2' in data['models']
    
    @patch('main_md.requests.get')
    def test_models_string_list_parsing(self, mock_get, client):
        """Test that simple list of strings is parsed correctly"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["model-a", "model-b", "model-c"]
        mock_get.return_value = mock_response
        
        response = client.get('/api/llm/models')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'models' in data
        assert 'model-a' in data['models']
    
    @patch('main_md.requests.get')
    def test_models_connection_error(self, mock_get, client):
        """Test error handling when LMStudio is not running"""
        mock_get.side_effect = Exception("Connection refused")
        
        response = client.get('/api/llm/models')
        assert response.status_code == 500
        
        data = json.loads(response.data)
        assert 'error' in data


class TestLeaderboardEndpoint:
    """Tests for the /api/leaderboard endpoint"""
    
    def test_leaderboard_endpoint_exists(self, client):
        """Test that the leaderboard endpoint exists"""
        response = client.get('/api/leaderboard')
        assert response.status_code == 200
    
    def test_leaderboard_returns_rankings(self, client):
        """Test that leaderboard returns rankings data"""
        response = client.get('/api/leaderboard')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'rankings' in data
        assert 'leaderboard' in data  # backward compatibility
        assert 'metric' in data
        assert 'categories' in data
    
    def test_leaderboard_default_metric(self, client):
        """Test that default metric is growth_rate"""
        response = client.get('/api/leaderboard')
        data = json.loads(response.data)
        assert data['metric'] == 'growth_rate'
    
    def test_leaderboard_health_metric(self, client):
        """Test health metric parameter"""
        response = client.get('/api/leaderboard?metric=health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['metric'] == 'health'
    
    def test_leaderboard_harvests_metric(self, client):
        """Test harvests metric parameter"""
        response = client.get('/api/leaderboard?metric=harvests')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['metric'] == 'harvests'
    
    def test_leaderboard_rankings_have_required_fields(self, client):
        """Test that each ranking entry has required fields"""
        response = client.get('/api/leaderboard')
        data = json.loads(response.data)
        
        for ranking in data['rankings']:
            assert 'id' in ranking
            assert 'name' in ranking
            assert 'growth_rate' in ranking
            assert 'health' in ranking
            assert 'harvests' in ranking
            assert 'rank' in ranking
    
    def test_leaderboard_category_filter(self, client):
        """Test category filter parameter"""
        # First get all plants to find a valid category
        response = client.get('/api/plants')
        plants = json.loads(response.data)

        if not plants or not plants[0].get('name'):
            pytest.skip("No plants in database to derive a category from")

        category = plants[0]['name'].lower()
        response = client.get(f'/api/leaderboard?category={category}')
        assert response.status_code == 200

        data = json.loads(response.data)
        # All returned plants should be in this category
        for ranking in data['rankings']:
            assert ranking['category'] == category
    
    def test_leaderboard_rankings_are_sorted(self, client):
        """Test that rankings are properly sorted by metric"""
        response = client.get('/api/leaderboard?metric=growth_rate')
        data = json.loads(response.data)
        
        rankings = data['rankings']
        if len(rankings) >= 2:
            # Check that rankings are in descending order by growth_rate
            for i in range(len(rankings) - 1):
                assert rankings[i]['growth_rate'] >= rankings[i + 1]['growth_rate']
    
    def test_leaderboard_ranks_are_assigned(self, client):
        """Test that ranks are correctly assigned (1, 2, 3, ...)"""
        response = client.get('/api/leaderboard')
        data = json.loads(response.data)
        
        rankings = data['rankings']
        for i, ranking in enumerate(rankings):
            assert ranking['rank'] == i + 1


class TestPlantsEndpoint:
    """Tests for /api/plants endpoint used by leaderboard"""
    
    def test_plants_endpoint_exists(self, client):
        """Test that plants endpoint exists"""
        response = client.get('/api/plants')
        assert response.status_code == 200
    
    def test_plants_returns_list(self, client):
        """Test that plants returns a list"""
        response = client.get('/api/plants')
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_plants_have_required_fields(self, client):
        """Test that plants have required fields for leaderboard"""
        response = client.get('/api/plants')
        data = json.loads(response.data)
        
        for plant in data:
            assert 'id' in plant
            assert 'name' in plant
            assert 'status' in plant


class TestLLMSettings:
    """Tests for LLM settings endpoints"""
    
    def test_llm_status_endpoint(self, client):
        """Test LLM status endpoint"""
        response = client.get('/api/llm/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'connected' in data
    
    def test_llm_settings_get(self, client):
        """Test getting LLM settings"""
        response = client.get('/api/llm/settings')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'url' in data
        assert 'model' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
