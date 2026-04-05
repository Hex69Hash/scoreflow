"""
Backend API tests for Assam Board Results Portal - Iteration 3
Tests: Board-specific dynamic inputs
- SEBA: 2 fields (Roll BXX-XXXX + Number)
- AHSEC: 3 fields (Roll numeric + Number + Registration Number)
Endpoints: /api/, /api/config, /api/check-result, /api/stats
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
        """Test GET /api/config returns configuration for both boards"""
        response = api_client.get(f"{BASE_URL}/api/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "current_year" in data
        assert "seba" in data
        assert "ahsec" in data
        
        # Verify SEBA config
        assert data["seba"]["latest_released_year"] == 2025
        assert "expected_release_note" in data["seba"]
        
        # Verify AHSEC config
        assert data["ahsec"]["is_current_year_released"] is False
        assert data["ahsec"]["latest_released_year"] == 2025
        assert "expected_release_note" in data["ahsec"]


class TestSEBACheckResult:
    """Test /api/check-result for SEBA board (2 fields: Roll BXX-XXXX + Number)"""

    def test_seba_b25_success(self, api_client):
        """Test SEBA B25 roll (2025) - should return success with redirect"""
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

    def test_seba_b26_not_released(self, api_client):
        """Test SEBA B26 roll (2026) - should return not_released modal"""
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
        assert "note" in data
        assert data["year"] == 2026

    def test_seba_b24_success(self, api_client):
        """Test SEBA B24 roll (2024) - should return success"""
        payload = {
            "board": "seba",
            "roll": "B24-1234",
            "number": "5678"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["year"] == 2024

    def test_seba_b23_unsupported(self, api_client):
        """Test SEBA B23 roll (2023) - should return unsupported_year error"""
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

    def test_seba_auto_normalize_roll(self, api_client):
        """Test SEBA auto-normalizes roll (B260816 -> B26-0816)"""
        payload = {
            "board": "seba",
            "roll": "B260816",  # No dash
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        # Should normalize and return not_released for 2026
        assert data["error_type"] == "not_released"
        assert data["year"] == 2026

    def test_seba_validation_empty_roll(self, api_client):
        """Test SEBA validation: empty roll"""
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

    def test_seba_validation_invalid_format(self, api_client):
        """Test SEBA validation: invalid roll format"""
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

    def test_seba_validation_empty_number(self, api_client):
        """Test SEBA validation: empty number"""
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

    def test_seba_validation_non_numeric_number(self, api_client):
        """Test SEBA validation: non-numeric number"""
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

    def test_seba_validation_short_number(self, api_client):
        """Test SEBA validation: number less than 3 digits"""
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


class TestAHSECCheckResult:
    """Test /api/check-result for AHSEC board (3 fields: Roll + Number + Registration Number)"""

    def test_ahsec_not_released(self, api_client):
        """Test AHSEC with valid inputs - should return not_released (is_current_year_released=False)"""
        payload = {
            "board": "ahsec",
            "roll": "0259",
            "number": "20060",
            "registration_number": "042283"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "not_released"
        assert data["title"] == "Result Not Released"
        assert "HS Examination Result" in data["subtitle"]
        assert "not been announced" in data["message"]
        assert "note" in data

    def test_ahsec_validation_empty_roll(self, api_client):
        """Test AHSEC validation: empty roll"""
        payload = {
            "board": "ahsec",
            "roll": "",
            "number": "20060",
            "registration_number": "042283"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "enter your roll" in data["error"].lower()

    def test_ahsec_validation_non_numeric_roll(self, api_client):
        """Test AHSEC validation: non-numeric roll"""
        payload = {
            "board": "ahsec",
            "roll": "ABC123",
            "number": "20060",
            "registration_number": "042283"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "digits" in data["error"].lower()

    def test_ahsec_validation_empty_number(self, api_client):
        """Test AHSEC validation: empty number"""
        payload = {
            "board": "ahsec",
            "roll": "0259",
            "number": "",
            "registration_number": "042283"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "enter your number" in data["error"].lower()

    def test_ahsec_validation_non_numeric_number(self, api_client):
        """Test AHSEC validation: non-numeric number"""
        payload = {
            "board": "ahsec",
            "roll": "0259",
            "number": "ABC",
            "registration_number": "042283"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "digits" in data["error"].lower()

    def test_ahsec_validation_empty_registration(self, api_client):
        """Test AHSEC validation: empty registration number"""
        payload = {
            "board": "ahsec",
            "roll": "0259",
            "number": "20060",
            "registration_number": ""
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "registration" in data["error"].lower()

    def test_ahsec_validation_non_numeric_registration(self, api_client):
        """Test AHSEC validation: non-numeric registration number"""
        payload = {
            "board": "ahsec",
            "roll": "0259",
            "number": "20060",
            "registration_number": "ABC123"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "digits" in data["error"].lower()

    def test_ahsec_missing_registration_field(self, api_client):
        """Test AHSEC validation: missing registration_number field entirely"""
        payload = {
            "board": "ahsec",
            "roll": "0259",
            "number": "20060"
            # registration_number missing
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "validation"
        assert "registration" in data["error"].lower()


class TestInvalidBoard:
    """Test invalid board handling"""

    def test_invalid_board(self, api_client):
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

    def test_seba_check_logged_to_db(self, api_client):
        """Test that SEBA check increases stats count"""
        # Get initial count
        stats_before = api_client.get(f"{BASE_URL}/api/stats").json()
        initial_count = stats_before["total_checks"]
        
        # Make a SEBA result check
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

    def test_ahsec_check_logged_to_db(self, api_client):
        """Test that AHSEC check increases stats count"""
        # Get initial count
        stats_before = api_client.get(f"{BASE_URL}/api/stats").json()
        initial_count = stats_before["total_checks"]
        
        # Make an AHSEC result check
        payload = {
            "board": "ahsec",
            "roll": "9999",
            "number": "9999",
            "registration_number": "9999"
        }
        api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        
        # Get count after
        stats_after = api_client.get(f"{BASE_URL}/api/stats").json()
        final_count = stats_after["total_checks"]
        
        # Count should increase by 1
        assert final_count == initial_count + 1
