from __future__ import annotations

import json


def test_post_lead_override_writes_audit_metadata(
    api_client,
    write_state,
    state_with_one_lead,
    state_path,
    sample_lead,
):
    write_state(state_with_one_lead)

    response = api_client.post(
        f"/api/leads/{sample_lead.id}/override",
        json={"action": "manual_review", "reason": "QA check"},
        headers={"Remote-User": "operator@example.pl"},
    )

    assert response.status_code == 200
    payload = response.json()
    override = payload["decision"]["metadata"]["dashboard_override"]
    assert override["action"] == "manual_review"
    assert override["actor"] == "operator@example.pl"
    assert override["previous_action"] == "send"
    assert override["reason"] == "QA check"

    saved = json.loads(state_path.read_text(encoding="utf-8"))
    saved_override = saved["decisions"][str(sample_lead.id)]["decision"]["metadata"]["dashboard_override"]
    assert saved_override["action"] == "manual_review"


def test_post_lead_override_send_requires_campaign(api_client, write_state, state_with_one_lead, sample_lead):
    write_state(state_with_one_lead)

    response = api_client.post(
        f"/api/leads/{sample_lead.id}/override",
        json={"action": "send", "reason": "approved"},
    )

    assert response.status_code == 422
