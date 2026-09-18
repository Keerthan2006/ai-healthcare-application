from fastapi.testclient import TestClient

import app

client = TestClient(app.app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "ai-service",
    }


def test_predict_success():
    app.FAILURE_MODE = "false"

    response = client.post(
        "/predict",
        json={"patient_id": "123", "data": "sample-healthcare-input"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert body["result"] == "mock-ai-result"
    assert body["input"] == {
        "patient_id": "123",
        "data": "sample-healthcare-input",
    }


def test_predict_failure():
    app.FAILURE_MODE = "true"

    response = client.post(
        "/predict",
        json={"patient_id": "123"},
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "failed",
        "reason": "AI service failure simulation",
    }

    app.FAILURE_MODE = "false"