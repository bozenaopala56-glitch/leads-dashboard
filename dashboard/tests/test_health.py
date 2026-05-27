from __future__ import annotations


def test_api_health_returns_ok(api_client):
    response = api_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_legacy_health_returns_ok(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
