from __future__ import annotations


def test_get_rulesets_lists_yaml_files(api_client):
    response = api_client.get("/api/rulesets")

    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload["items"]}
    assert "decision_gates.yml" in names
    assert "campaigns.yml" in names
    assert all(item["name"].endswith((".yml", ".yaml")) for item in payload["items"])


def test_get_rulesets_ignores_symlinks_outside_rules_dir(api_client, tmp_path, monkeypatch):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    outside = tmp_path / "outside.yml"
    outside.write_text("secret: true\n", encoding="utf-8")
    (rules_dir / "safe.yml").write_text("safe: true\n", encoding="utf-8")
    (rules_dir / "outside.yml").symlink_to(outside)
    monkeypatch.setenv("LEADPIPE_RULES", str(rules_dir))

    response = api_client.get("/api/rulesets")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()["items"]}
    assert names == {"safe.yml"}

    response = api_client.get("/api/rulesets/outside.yml")

    assert response.status_code == 404
