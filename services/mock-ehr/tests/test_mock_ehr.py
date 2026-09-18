from fastapi.testclient import TestClient

import app

client = TestClient(app.app)


def test_health():
    app.EHR_FAILURE_MODE = "normal"

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "mock-ehr",
        "mode": "normal",
    }


def test_sync_success():
    app.EHR_FAILURE_MODE = "normal"

    response = client.post(
        "/sync",
        json={"job_id": "test-job-123"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert body["job_id"] == "test-job-123"


def test_sync_failure():
    app.EHR_FAILURE_MODE = "failure"

    response = client.post(
        "/sync",
        json={"job_id": "test-job-123"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert body["job_id"] == "test-job-123"

    app.EHR_FAILURE_MODE = "normal"