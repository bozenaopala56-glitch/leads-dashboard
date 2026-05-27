from __future__ import annotations


def test_get_decisions_returns_decision_rows(
    api_client,
    write_state,
    state_with_one_lead,
    sample_lead,
):
    write_state(state_with_one_lead)

    response = api_client.get("/api/decisions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    row = payload["items"][0]
    assert row["lead_id"] == str(sample_lead.id)
    assert row["domain"] == "example.pl"
    assert row["decision"]["action"] == "send"
    assert row["trace"]["winning_rule"] == "conversion_fit"


def test_get_decisions_empty_state(api_client):
    response = api_client.get("/api/decisions")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_post_export_returns_csv_for_send_decisions(
    api_client,
    write_state,
    state_with_one_lead,
):
    write_state(state_with_one_lead)

    response = api_client.post("/api/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "firma,domena,email,telefon,kampania,subject,evidence_1,evidence_2,evidence_3,confidence,suppression_status" in body
    assert "Example Sp. z o.o.,example.pl,biuro@example.pl" in body
