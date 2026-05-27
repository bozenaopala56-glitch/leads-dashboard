from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

LEADPIPE_ROOT = Path("/tmp/leadpipe-t0")
if str(LEADPIPE_ROOT) not in sys.path:
    sys.path.insert(0, str(LEADPIPE_ROOT))
DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from leadpipe.models import (  # noqa: E402
    CampaignDecision,
    DecisionAction,
    DecisionTrace,
    Lead,
    LeadStatus,
    RuleEvaluation,
)


@pytest.fixture
def state_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / ".leadpipe" / "state.json"
    monkeypatch.setenv("LEADPIPE_STATE", str(path))
    return path


@pytest.fixture
def empty_state() -> dict:
    return {"leads": [], "scans": {}, "decisions": {}}


@pytest.fixture
def sample_lead() -> Lead:
    return Lead(
        input_domain="https://www.example.pl/",
        normalized_domain="example.pl",
        company_name="Example Sp. z o.o.",
        nip="1234563218",
        source="sample",
        contact_email="biuro@example.pl",
        status=LeadStatus.NEW,
    )


@pytest.fixture
def sample_lead_json(sample_lead: Lead) -> dict:
    return sample_lead.model_dump(mode="json")


@pytest.fixture
def sample_scan_payload(sample_lead: Lead) -> dict:
    lead_id = str(sample_lead.id)
    return {
        "t0": {
            "signals": {"t0_score": 72, "has_https": True, "old_tech": True},
            "scan_result": {"http_status": 200, "final_url": "https://example.pl"},
        },
        "t0_5": {
            "signals": {"nip_present": True, "vat_active": True, "company_confirmed": True},
            "enrichment": {"source": "fixture"},
        },
        "t1": {
            "signals": {
                "campaign_confidence": 0.81,
                "contactability": 85,
                "has_email": True,
            },
            "contact": {"emails": ["biuro@example.pl"]},
        },
        "lead_id": lead_id,
    }


@pytest.fixture
def sample_decision_payload(sample_lead: Lead) -> dict:
    decision = CampaignDecision(
        lead_id=sample_lead.id,
        action=DecisionAction.SEND,
        campaign="REDESIGN_CONVERSION",
        confidence=0.84,
        decision_reason="Strong conversion signal",
        ruleset_version="test",
        rule_key="conversion_fit",
    )
    trace = DecisionTrace(
        lead_id=sample_lead.id,
        ruleset_version="test",
        evaluated_rules=[RuleEvaluation(rule_key="conversion_fit", result=True)],
        winning_rule="conversion_fit",
        decision_reason="Strong conversion signal",
    )
    return {
        "decision": decision.model_dump(mode="json"),
        "trace": trace.model_dump(mode="json"),
    }


@pytest.fixture
def state_with_one_lead(
    sample_lead_json: dict,
    sample_scan_payload: dict,
    sample_decision_payload: dict,
) -> dict:
    lead_id = sample_lead_json["id"]
    return {
        "leads": [sample_lead_json],
        "scans": {lead_id: sample_scan_payload},
        "decisions": {lead_id: sample_decision_payload},
    }


@pytest.fixture
def write_state(state_path: Path):
    def _write(payload: dict) -> Path:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(payload), encoding="utf-8")
        return state_path

    return _write


@pytest.fixture
def api_client(state_path: Path) -> TestClient:
    from backend.app import app

    return TestClient(app)


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    path = tmp_path / "leads.csv"
    path.write_text(
        "domain,url,company_name,nip,source,contact_email,notes\n"
        "example.pl,https://example.pl,Example,1234563218,sample,biuro@example.pl,ok\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def invalid_csv_file(tmp_path: Path) -> Path:
    path = tmp_path / "bad.csv"
    path.write_text(
        "domain,url,company_name,nip,source,contact_email,notes\n"
        ",https://example.pl,Example,123,sample,bad-email,broken\n",
        encoding="utf-8",
    )
    return path
