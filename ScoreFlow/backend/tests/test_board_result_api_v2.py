"""
Backend API tests for Assam Board Results Portal - Iteration 2
Tests: Two-field input (Roll + Number), year extraction, result availability logic
Endpoints: /api/config, /api/normalize-roll, /api/check-result, /api/stats
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


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestRootAPI:
    """Test root API endpoint"""

    def test_root_endpoint(self, api_client):
        """Test GET /api/ returns welcome message"""
        response = api_client.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Assam Board" in data["message"]


class TestConfigAPI:
    """Test /api/config endpoint"""

    def test_get_config(self, api_client):
        """Test GET /api/config returns configuration"""
        response = api_client.get(f"{BASE_URL}/api/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "latest_released_year" in data
        assert "upcoming_year" in data
        assert "min_supported_year" in data
        assert "expected_release_date" in data
        assert "boards" in data
        
        # Verify config values
        assert data["latest_released_year"] == 2025
        assert data["upcoming_year"] == 2026
        assert data["min_supported_year"] == 2024
        assert data["expected_release_date"] == "10 April 2026"
        
        # Verify boards
        assert "seba" in data["boards"]
        assert "ahsec" in data["boards"]
        assert data["boards"]["seba"]["name"] == "SEBA"
        assert data["boards"]["seba"]["exam"] == "HSLC"
        assert data["boards"]["ahsec"]["name"] == "AHSEC"
        assert data["boards"]["ahsec"]["exam"] == "HS"


class TestNormalizeRollAPI:
    """Test /api/normalize-roll endpoint"""

    def test_normalize_roll_with_dash(self, api_client):
        """Test normalize roll that already has dash"""
        response = api_client.post(f"{BASE_URL}/api/normalize-roll", json={"roll": "B26-0816"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["normalized"] == "B26-0816"

    def test_normalize_roll_without_dash(self, api_client):
        """Test normalize roll without dash - should insert dash"""
        response = api_client.post(f"{BASE_URL}/api/normalize-roll", json={"roll": "B260816"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["normalized"] == "B26-0816"

    def test_normalize_roll_lowercase(self, api_client):
        """Test normalize roll converts to uppercase"""
        response = api_client.post(f"{BASE_URL}/api/normalize-roll", json={"roll": "b26-0816"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["normalized"] == "B26-0816"

    def test_normalize_roll_with_spaces(self, api_client):
        """Test normalize roll removes spaces"""
        response = api_client.post(f"{BASE_URL}/api/normalize-roll", json={"roll": " B26 0816 "})
        assert response.status_code == 200
        
        data = response.json()
        assert data["normalized"] == "B26-0816"


class TestCheckResultAPI:
    """Test /api/check-result endpoint - comprehensive scenarios"""

    def test_check_result_2025_success_seba(self, api_client):
        """Test successful result check for SEBA 2025 (released year)"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["board_name"] == "SEBA"
        assert data["exam_name"] == "HSLC Examination Result 2025"
        assert data["roll"] == "B25-0816"
        assert data["number"] == "0238"
        assert data["year"] == 2025
        assert "result_url" in data
        assert data["result_url"] == "https://resultsassam.nic.in/"

    def test_check_result_2025_success_ahsec(self, api_client):
        """Test successful result check for AHSEC 2025"""
        payload = {
            "board": "ahsec",
            "roll": "B25-1234",
            "number": "5678"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["board_name"] == "AHSEC"
        assert data["exam_name"] == "HS Examination Result 2025"
        assert data["year"] == 2025

    def test_check_result_2024_success(self, api_client):
        """Test successful result check for 2024 (min supported year)"""
        payload = {
            "board": "seba",
            "roll": "B24-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["year"] == 2024

    def test_check_result_2026_not_released(self, api_client):
        """Test 2026 result - should return not_released modal data"""
        payload = {
            "board": "seba",
            "roll": "B26-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "not_released"
        assert data["title"] == "Result Not Released"
        assert data["subtitle"] == "HSLC Examination Result 2026"
        assert "not been announced" in data["message"]
        assert data["note"] == "Expected: 10 April 2026"
        assert data["year"] == 2026

    def test_check_result_2023_unsupported(self, api_client):
        """Test 2023 result - should return unsupported_year error"""
        payload = {
            "board": "seba",
            "roll": "B23-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "unsupported_year"
        assert "not available" in data["error"]
        assert data["year"] == 2023

    def test_check_result_2027_unsupported(self, api_client):
        """Test 2027 result - should return unsupported_year error"""
        payload = {
            "board": "seba",
            "roll": "B27-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "unsupported_year"
        assert data["year"] == 2027

    def test_check_result_empty_roll(self, api_client):
        """Test validation: empty roll number"""
        payload = {
            "board": "seba",
            "roll": "",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "enter your roll" in data["error"].lower()

    def test_check_result_invalid_roll_format(self, api_client):
        """Test validation: invalid roll format"""
        payload = {
            "board": "seba",
            "roll": "12345",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "BXX-XXXX" in data["error"]

    def test_check_result_empty_number(self, api_client):
        """Test validation: empty number"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": ""
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "enter your number" in data["error"].lower()

    def test_check_result_non_numeric_number(self, api_client):
        """Test validation: non-numeric number"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "ABC123"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "digits" in data["error"].lower()

    def test_check_result_short_number(self, api_client):
        """Test validation: number less than 3 digits"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "12"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "at least 3 digits" in data["error"]

    def test_check_result_invalid_board(self, api_client):
        """Test validation: invalid board"""
        payload = {
            "board": "invalid",
            "roll": "B25-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "board" in data["error"].lower()

    def test_check_result_auto_normalize_roll(self, api_client):
        """Test that backend auto-normalizes roll (B260816 -> B26-0816)"""
        payload = {
            "board": "seba",
            "roll": "b260816",  # lowercase, no dash
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Should normalize and return not_released for 2026
        assert data["error_type"] == "not_released"
        assert data["year"] == 2026

    def test_check_result_whitespace_handling(self, api_client):
        """Test that whitespace is trimmed from inputs"""
        payload = {
            "board": "seba",
            "roll": "  B25-0816  ",
            "number": "  0238  "
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["roll"] == "B25-0816"
        assert data["number"] == "0238"


class TestStatsAPI:
    """Test /api/stats endpoint"""

    def test_get_stats(self, api_client):
        """Test GET /api/stats returns total checks count"""
        response = api_client.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_checks" in data
        assert isinstance(data["total_checks"], int)
        assert data["total_checks"] >= 0


class TestDataPersistence:
    """Test that result checks are logged to database"""

    def test_result_check_logged_to_db(self, api_client):
        """Test that successful check increases stats count"""
        # Get initial count
        stats_before = api_client.get(f"{BASE_URL}/api/stats").json()
        initial_count = stats_before["total_checks"]
        
        # Make a result check
        payload = {
            "board": "seba",
            "roll": "B25-9999",
            "number": "9999"
        }
        api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        
        # Get count after
        stats_after = api_client.get(f"{BASE_URL}/api/stats").json()
        final_count = stats_after["total_checks"]
        
        # Count should increase by 1
        assert final_count == initial_count + 1
