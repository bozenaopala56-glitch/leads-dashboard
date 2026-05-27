from __future__ import annotations

import argparse


def test_get_batches_returns_empty_list(api_client):
    response = api_client.get("/api/batches")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_get_batches_groups_leads_by_batch_id(api_client, write_state, sample_lead_json):
    sample_lead_json["batch_id"] = "11111111-1111-1111-1111-111111111111"
    write_state({"leads": [sample_lead_json], "scans": {}, "decisions": {}})

    response = api_client.get("/api/batches")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "source": "sample",
            "lead_count": 1,
            "status_counts": {"new": 1},
        }
    ]


def test_post_batches_imports_csv_and_returns_snapshot(
    api_client,
    csv_file,
    write_state,
    state_with_one_lead,
    monkeypatch,
):
    calls = []

    def fake_import(args: argparse.Namespace) -> int:
        calls.append(args.file)
        write_state(state_with_one_lead)
        return 0

    monkeypatch.setattr("leadpipe.cli.command_import", fake_import)

    with csv_file.open("rb") as handle:
        response = api_client.post(
            "/api/batches",
            files={"file": ("leads.csv", handle, "text/csv")},
        )

    assert response.status_code == 201
    assert calls
    payload = response.json()
    assert payload["imported"] is True
    assert payload["state"]["leads"][0]["normalized_domain"] == "example.pl"


def test_post_batches_rejects_invalid_csv(api_client, invalid_csv_file):
    with invalid_csv_file.open("rb") as handle:
        response = api_client.post(
            "/api/batches",
            files={"file": ("bad.csv", handle, "text/csv")},
        )

    assert response.status_code == 422
    assert response.json()["detail"][0]["row"] == 2
