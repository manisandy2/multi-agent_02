import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# =========================
# ✅ 1. Basic Health Test
# =========================
def test_api_running():
    response = client.get("/")
    assert response.status_code == 200


# =========================
# ✅ 2. Negative Review → Complaint Flow
# =========================
def test_negative_review_creates_complaint():
    payload = {
        "comment": "Very bad experience",
        "star_rating": 1,
        "reviewer": "Sam",
        "location_name": "K.K. Nagar",
        "review_date": "2024-01-01"
    }

    response = client.post("/process-review", json=payload)
    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    # Core checks
    assert data["status"] == "success"
    assert result["reply"] is not None
    assert result["complaint_link"] is not None

    # Decision checks
    decision = result["decision"]
    assert decision["classification"]["sentiment"] == "negative"
    assert decision["create_ticket"] is True
    assert decision["action"] == "complaint"


# =========================
# ✅ 3. Positive Review → No Complaint
# =========================
def test_positive_review_no_complaint():
    payload = {
        "comment": "Great service, very happy!",
        "star_rating": 5,
        "reviewer": "John",
        "location_name": "Anna Nagar",
        "review_date": "2024-01-01"
    }

    response = client.post("/process-review", json=payload)
    assert response.status_code == 200

    data = response.json()
    result = data["data"]

    assert result["complaint_link"] is None or result["complaint_link"] == ""
    assert result["reply"] is not None


# =========================
# ✅ 4. Fallback Scenario Test
# =========================
def test_fallback_response():
    payload = {
        "comment": "",   # invalid content triggers fallback logic
        "star_rating": 1,
        "reviewer": "Test",
        "location_name": "Anna Nagar",
        "review_date": "2024-01-01"
    }

    response = client.post("/process-review", json=payload)
    assert response.status_code == 200

    data = response.json()
    result = data["data"]
    decision = result["decision"]

    # ✅ Ensure system handled gracefully
    assert result["reply"] is not None

    # ✅ Confidence should be low for poor input
    assert decision["confidence"] <= 0.6

    # ✅ Optional: fallback indicator (if exists)
    if "reason" in decision:
        assert isinstance(decision["reason"], str)


# =========================
# ✅ 5. Logs Validation
# =========================
def test_logs_sequence():
    payload = {
        "comment": "Bad experience",
        "star_rating": 1,
        "reviewer": "Sam",
        "location_name": "Anna Nagar",
        "review_date": "2024-01-01"
    }

    response = client.post("/process-review", json=payload)
    assert response.status_code == 200   # ✅ IMPORTANT

    data = response.json()
    logs = data["data"]["logs"]

    messages = [log["message"] for log in logs]

    assert "Processing started" in messages[0]
    assert any("Reply generation started" in m for m in messages)
    assert any("Validation started" in m for m in messages)


# =========================
# ✅ 6. Response Structure Test
# =========================
def test_response_structure():
    payload = {
        "comment": "Average service",
        "star_rating": 3,
        "reviewer": "Alex",
        "location_name": "Anna Nagar",
        "review_date": "2024-01-01"
    }

    response = client.post("/process-review", json=payload)
    data = response.json()

    assert "status" in data
    assert "data" in data

    result = data["data"]

    required_fields = [
        "job_id",
        "status",
        "reply",
        "decision",
        "logs",
        "history"
    ]

    for field in required_fields:
        assert field in result