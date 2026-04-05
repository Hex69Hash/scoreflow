"""
Backend API tests for Assam Board Results Portal
Tests: /api/boards and /api/check-result endpoints
"""
import pytest
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load frontend .env to get EXPO_PUBLIC_BACKEND_URL
frontend_env = Path(__file__).parent.parent.parent / 'frontend' / '.env'
load_dotenv(frontend_env)

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL')
if not BASE_URL:
    raise ValueError("EXPO_PUBLIC_BACKEND_URL not found in environment")
BASE_URL = BASE_URL.rstrip('/')

class TestBoardsAPI:
    """Test /api/boards endpoint"""

    def test_get_boards_success(self):
        """Test GET /api/boards returns board data"""
        response = requests.get(f"{BASE_URL}/api/boards")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Verify SEBA board
        seba = next((b for b in data if b['board'] == 'seba'), None)
        assert seba is not None
        assert seba['name'] == 'SEBA (Class 10 - HSLC)'
        assert seba['full_name'] == 'Board of Secondary Education, Assam'
        assert 'result_url' in seba
        assert len(seba['years']) == 3
        
        # Verify AHSEC board
        ahsec = next((b for b in data if b['board'] == 'ahsec'), None)
        assert ahsec is not None
        assert ahsec['name'] == 'AHSEC (Class 12 - HS)'
        assert ahsec['full_name'] == 'Assam Higher Secondary Education Council'
        assert 'result_url' in ahsec
        assert len(ahsec['years']) == 3

    def test_get_board_by_code_seba(self):
        """Test GET /api/boards/seba"""
        response = requests.get(f"{BASE_URL}/api/boards/seba")
        assert response.status_code == 200
        
        data = response.json()
        assert data['board'] == 'seba'
        assert data['name'] == 'SEBA (Class 10 - HSLC)'

    def test_get_board_by_code_ahsec(self):
        """Test GET /api/boards/ahsec"""
        response = requests.get(f"{BASE_URL}/api/boards/ahsec")
        assert response.status_code == 200
        
        data = response.json()
        assert data['board'] == 'ahsec'
        assert data['name'] == 'AHSEC (Class 12 - HS)'

    def test_get_board_invalid_code(self):
        """Test GET /api/boards with invalid code"""
        response = requests.get(f"{BASE_URL}/api/boards/invalid")
        assert response.status_code == 200
        
        data = response.json()
        assert 'error' in data
        assert data['error'] == 'Board not found'


class TestCheckResultAPI:
    """Test /api/check-result endpoint"""

    def test_check_result_success_seba_2025(self):
        """Test successful result check for SEBA 2025"""
        payload = {
            "board": "seba",
            "year": 2025,
            "roll_number": "123456"
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True
        assert data['board_name'] == 'SEBA (Class 10 - HSLC)'
        assert data['year'] == 2025
        assert data['roll_number'] == '123456'
        assert 'result_url' in data
        assert data['result_url'] == 'https://resultsassam.nic.in/'

    def test_check_result_success_ahsec_2024(self):
        """Test successful result check for AHSEC 2024"""
        payload = {
            "board": "ahsec",
            "year": 2024,
            "roll_number": "9876"
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True
        assert data['board_name'] == 'AHSEC (Class 12 - HS)'
        assert data['year'] == 2024
        assert data['roll_number'] == '9876'
        assert 'result_url' in data

    def test_check_result_empty_roll_number(self):
        """Test validation: empty roll number"""
        payload = {
            "board": "seba",
            "year": 2025,
            "roll_number": ""
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is False
        assert 'error' in data
        assert 'required' in data['error'].lower()

    def test_check_result_short_roll_number(self):
        """Test validation: roll number less than 4 digits"""
        payload = {
            "board": "seba",
            "year": 2025,
            "roll_number": "123"
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is False
        assert 'error' in data
        assert '4 digits' in data['error']

    def test_check_result_non_numeric_roll_number(self):
        """Test validation: non-numeric roll number"""
        payload = {
            "board": "seba",
            "year": 2025,
            "roll_number": "12AB34"
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is False
        assert 'error' in data
        assert 'digits' in data['error'].lower()

    def test_check_result_disabled_year(self):
        """Test validation: year 2026 is disabled"""
        payload = {
            "board": "seba",
            "year": 2026,
            "roll_number": "123456"
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is False
        assert 'error' in data
        assert '2026' in data['error']

    def test_check_result_invalid_board(self):
        """Test validation: invalid board"""
        payload = {
            "board": "invalid",
            "year": 2025,
            "roll_number": "123456"
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is False
        assert 'error' in data
        assert 'board' in data['error'].lower()

    def test_check_result_whitespace_handling(self):
        """Test that whitespace in roll number is trimmed"""
        payload = {
            "board": "seba",
            "year": 2025,
            "roll_number": "  123456  "
        }
        response = requests.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data['success'] is True
        assert data['roll_number'] == '123456'


class TestStatsAPI:
    """Test /api/stats endpoint"""

    def test_get_stats(self):
        """Test GET /api/stats returns total checks count"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert 'total_checks' in data
        assert isinstance(data['total_checks'], int)
        assert data['total_checks'] >= 0
