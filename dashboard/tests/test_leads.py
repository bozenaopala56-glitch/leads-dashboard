from __future__ import annotations

from leadpipe.models import Lead, LeadStatus


def test_get_leads_returns_rows_with_scan_and_decision_aggregates(
    api_client,
    write_state,
    state_with_one_lead,
    sample_lead,
):
    write_state(state_with_one_lead)

    response = api_client.get("/api/leads")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    row = payload["items"][0]
    assert row["id"] == str(sample_lead.id)
    assert row["domain"] == "example.pl"
    assert row["company"] == "Example Sp. z o.o."
    assert row["t0_score"] == 72
    assert row["t1_signals"]["campaign_confidence"] == 0.81
    assert row["decision"]["action"] == "send"
    assert row["decision"]["confidence"] == 0.84
    assert row["decision"]["rule_key"] == "conversion_fit"


def test_get_leads_handles_empty_state(api_client):
    response = api_client.get("/api/leads")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_get_leads_supports_pagination_and_filters(api_client, write_state, sample_lead_json):
    other = Lead(
        input_domain="other.pl",
        normalized_domain="other.pl",
        source="partner",
        status=LeadStatus.DECIDED,
    ).model_dump(mode="json")
    decisions = {
        other["id"]: {
            "decision": {
                "lead_id": other["id"],
                "action": "manual_review",
                "campaign": None,
                "confidence": 0.3,
                "ruleset_version": "test",
                "rule_key": "qa",
            },
            "trace": {"decision_reason": "qa"},
        }
    }
    write_state({"leads": [sample_lead_json, other], "scans": {}, "decisions": decisions})

    response = api_client.get("/api/leads?status=decided&source=partner&action=manual_review&page=1&page_size=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["domain"] == "other.pl"


def test_get_lead_detail_returns_lead_scans_decision_trace(
    api_client,
    write_state,
    state_with_one_lead,
    sample_lead,
):
    write_state(state_with_one_lead)

    response = api_client.get(f"/api/leads/{sample_lead.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["lead"]["id"] == str(sample_lead.id)
    assert payload["scans"]["t0"]["signals"]["old_tech"] is True
    assert payload["scans"]["t0_5"]["signals"]["vat_active"] is True
    assert payload["scans"]["t1"]["signals"]["has_email"] is True
    assert payload["decision"]["action"] == "send"
    assert payload["trace"]["winning_rule"] == "conversion_fit"


def test_get_lead_detail_returns_404_for_missing_lead(api_client):
    response = api_client.get("/api/leads/missing")

    assert response.status_code == 404
