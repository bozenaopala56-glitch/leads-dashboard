from __future__ import annotations


def test_get_rulesets_lists_yaml_files(api_client):
    response = api_client.get("/api/rulesets")

    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload["items"]}
    assert "decision_gates.yml" in names
    assert "campaigns.yml" in names
    assert all(item["name"].endswith(".yml") for item in payload["items"])
