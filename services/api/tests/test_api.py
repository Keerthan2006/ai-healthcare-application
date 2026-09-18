from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "api",
    }


def test_status():
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    assert response.json() == {
        "service": "healthcare-api",
        "version": "v1",
        "status": "running",
    }


def test_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200