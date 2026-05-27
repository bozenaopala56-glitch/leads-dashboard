from __future__ import annotations

from backend.services.state_service import StateStore, empty_state


def test_load_state_missing_file_returns_empty_state(state_path):
    assert StateStore(state_path).load_state() == empty_state()


def test_load_state_invalid_json_returns_empty_state(state_path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{broken", encoding="utf-8")

    assert StateStore(state_path).load_state() == empty_state()


def test_load_state_invalid_shape_returns_empty_state(state_path):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("[]", encoding="utf-8")

    assert StateStore(state_path).load_state() == empty_state()


def test_load_state_partial_shape_normalizes_sections(state_path, write_state):
    write_state({"leads": "bad", "scans": [], "decisions": None})

    assert StateStore(state_path).load_state() == empty_state()


def test_load_state_preserves_raw_scans_and_decisions(
    state_path,
    write_state,
    state_with_one_lead,
    sample_lead,
):
    write_state(state_with_one_lead)

    snapshot = StateStore(state_path).load_snapshot()

    assert snapshot.leads[0].normalized_domain == sample_lead.normalized_domain
    assert snapshot.scans[str(sample_lead.id)]["t0"]["signals"]["t0_score"] == 72
    assert snapshot.decisions[str(sample_lead.id)]["decision"]["action"] == "send"
