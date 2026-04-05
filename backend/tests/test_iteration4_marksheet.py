"""
Backend API tests for Assam Board Results Portal - Iteration 4
New features tested:
- Full marksheet data (student_name, subjects array, total_marks, percentage, result_status)
- /api/generate-image endpoint (Pillow PNG generation)
- Updated official URLs (SEBA: sebaonline.org/results, AHSEC: ahsec.assam.gov.in/results)
Endpoints: /api/check-result, /api/generate-image
"""
import pytest
import requests
import os
import base64
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


class TestSEBAMarksheetData:
    """Test /api/check-result returns full marksheet data for SEBA"""

    def test_seba_b25_full_marksheet_data(self, api_client):
        """Test SEBA B25-0816 + 0238 returns complete marksheet with all fields"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # Verify basic fields
        assert data["board_name"] == "SEBA"
        assert data["exam_name"] == "HSLC Examination Result 2025"
        assert data["full_name"] == "Board of Secondary Education, Assam"
        assert data["roll"] == "B25-0816"
        assert data["number"] == "0238"
        assert data["year"] == 2025
        
        # NEW: Verify student_name exists and is non-empty
        assert "student_name" in data
        assert isinstance(data["student_name"], str)
        assert len(data["student_name"]) > 0
        print(f"Student name: {data['student_name']}")
        
        # NEW: Verify subjects array
        assert "subjects" in data
        assert isinstance(data["subjects"], list)
        assert len(data["subjects"]) == 6  # SEBA has 6 subjects
        
        # Verify each subject has required fields
        for subject in data["subjects"]:
            assert "subject" in subject
            assert "marks" in subject
            assert "full_marks" in subject
            assert isinstance(subject["subject"], str)
            assert isinstance(subject["marks"], int)
            assert isinstance(subject["full_marks"], int)
            assert subject["full_marks"] == 100
            assert 0 <= subject["marks"] <= 100
        
        print(f"Subjects: {[s['subject'] for s in data['subjects']]}")
        
        # NEW: Verify total_marks
        assert "total_marks" in data
        assert isinstance(data["total_marks"], int)
        calculated_total = sum(s["marks"] for s in data["subjects"])
        assert data["total_marks"] == calculated_total
        print(f"Total marks: {data['total_marks']}")
        
        # NEW: Verify full_total_marks
        assert "full_total_marks" in data
        assert data["full_total_marks"] == 600  # 6 subjects * 100
        
        # NEW: Verify percentage
        assert "percentage" in data
        assert isinstance(data["percentage"], (int, float))
        assert 0 <= data["percentage"] <= 100
        expected_percentage = round((data["total_marks"] / data["full_total_marks"]) * 100, 2)
        assert data["percentage"] == expected_percentage
        print(f"Percentage: {data['percentage']}%")
        
        # NEW: Verify result_status (PASS/FAIL)
        assert "result_status" in data
        assert data["result_status"] in ["PASS", "FAIL"]
        
        # Verify pass logic: all subjects >= 30 and percentage >= 30
        all_passed = all(s["marks"] >= 30 for s in data["subjects"])
        if all_passed and data["percentage"] >= 30:
            assert data["result_status"] == "PASS"
        else:
            assert data["result_status"] == "FAIL"
        print(f"Result: {data['result_status']}")
        
        # NEW: Verify updated official URL
        assert data["result_url"] == "https://sebaonline.org/results"

    def test_seba_deterministic_generation(self, api_client):
        """Test that same roll+number generates same result (deterministic)"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "0238"
        }
        
        # Make two requests with same data
        response1 = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        response2 = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Should return identical data
        assert data1["student_name"] == data2["student_name"]
        assert data1["subjects"] == data2["subjects"]
        assert data1["total_marks"] == data2["total_marks"]
        assert data1["percentage"] == data2["percentage"]
        assert data1["result_status"] == data2["result_status"]

    def test_seba_different_rolls_different_results(self, api_client):
        """Test that different roll numbers generate different results"""
        payload1 = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "0238"
        }
        payload2 = {
            "board": "seba",
            "roll": "B25-1234",
            "number": "5678"
        }
        
        response1 = api_client.post(f"{BASE_URL}/api/check-result", json=payload1)
        response2 = api_client.post(f"{BASE_URL}/api/check-result", json=payload2)
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Different inputs should generate different results
        assert data1["student_name"] != data2["student_name"]


class TestAHSECMarksheetData:
    """Test /api/check-result for AHSEC (currently returns not_released)"""

    def test_ahsec_not_released_with_updated_url(self, api_client):
        """Test AHSEC returns not_released modal with updated URL"""
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


class TestGenerateImageEndpoint:
    """Test /api/generate-image endpoint (NEW in iteration 4)"""

    def test_generate_image_success(self, api_client):
        """Test /api/generate-image returns base64 PNG image"""
        # First get a valid result
        check_payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "0238"
        }
        check_response = api_client.post(f"{BASE_URL}/api/check-result", json=check_payload)
        result_data = check_response.json()
        
        # Now generate image from result data
        image_response = api_client.post(f"{BASE_URL}/api/generate-image", json=result_data)
        assert image_response.status_code == 200
        
        image_data = image_response.json()
        assert image_data["success"] is True
        assert "image" in image_data
        
        # Verify it's valid base64
        assert isinstance(image_data["image"], str)
        assert len(image_data["image"]) > 0
        
        # Try to decode base64 to verify it's valid
        try:
            decoded = base64.b64decode(image_data["image"])
            assert len(decoded) > 0
            # PNG files start with specific magic bytes
            assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
            print(f"Generated PNG image size: {len(decoded)} bytes")
        except Exception as e:
            pytest.fail(f"Failed to decode base64 image: {e}")

    def test_generate_image_with_minimal_data(self, api_client):
        """Test /api/generate-image with minimal required data"""
        minimal_data = {
            "full_name": "Test Board",
            "exam_name": "Test Exam 2025",
            "student_name": "Test Student",
            "roll": "B25-0001",
            "number": "0001",
            "year": 2025,
            "subjects": [
                {"subject": "Math", "marks": 85, "full_marks": 100},
                {"subject": "Science", "marks": 90, "full_marks": 100}
            ],
            "total_marks": 175,
            "full_total_marks": 200,
            "percentage": 87.5,
            "result_status": "PASS"
        }
        
        response = api_client.post(f"{BASE_URL}/api/generate-image", json=minimal_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "image" in data

    def test_generate_image_with_registration_number(self, api_client):
        """Test /api/generate-image includes registration number if provided"""
        data_with_reg = {
            "full_name": "AHSEC",
            "exam_name": "HS Examination 2025",
            "student_name": "Test Student",
            "roll": "0259",
            "number": "20060",
            "registration_number": "042283",
            "year": 2025,
            "subjects": [
                {"subject": "Physics", "marks": 85, "full_marks": 100}
            ],
            "total_marks": 85,
            "full_total_marks": 100,
            "percentage": 85.0,
            "result_status": "PASS"
        }
        
        response = api_client.post(f"{BASE_URL}/api/generate-image", json=data_with_reg)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "image" in data


class TestUpdatedOfficialURLs:
    """Test that official URLs have been updated in iteration 4"""

    def test_seba_official_url_updated(self, api_client):
        """Test SEBA result_url is https://sebaonline.org/results"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        data = response.json()
        
        assert data["result_url"] == "https://sebaonline.org/results"
        # Old URL was https://resultsassam.nic.in/ - verify it's NOT that
        assert data["result_url"] != "https://resultsassam.nic.in/"


class TestSubjectMarksValidation:
    """Test subject marks are within valid ranges"""

    def test_all_marks_within_range(self, api_client):
        """Test all subject marks are between 0-100"""
        payload = {
            "board": "seba",
            "roll": "B25-0816",
            "number": "0238"
        }
        response = api_client.post(f"{BASE_URL}/api/check-result", json=payload)
        data = response.json()
        
        for subject in data["subjects"]:
            assert 0 <= subject["marks"] <= 100, f"Marks {subject['marks']} out of range for {subject['subject']}"
            assert subject["marks"] >= 28, f"Marks too low (min should be 28): {subject['marks']}"
            assert subject["marks"] <= 97, f"Marks too high (max should be 97): {subject['marks']}"
