from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from leadpipe.models import Lead

from ..deps import get_state_store
from ..services.state_service import StateSnapshot, StateStore

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _signals(scan: dict[str, Any], layer: str) -> dict[str, Any]:
    section = scan.get(layer) or {}
    return section.get("signals") or {}


def _decision_payload(snapshot: StateSnapshot, lead_id: str) -> dict[str, Any] | None:
    entry = snapshot.decisions.get(lead_id) or {}
    decision = entry.get("decision") if isinstance(entry, dict) else None
    return decision if isinstance(decision, dict) else None


def _trace_payload(snapshot: StateSnapshot, lead_id: str) -> dict[str, Any] | None:
    entry = snapshot.decisions.get(lead_id) or {}
    trace = entry.get("trace") if isinstance(entry, dict) else None
    return trace if isinstance(trace, dict) else None


def _lead_row(lead: Lead, snapshot: StateSnapshot) -> dict[str, Any]:
    lead_id = str(lead.id)
    scan = snapshot.scans.get(lead_id) or {}
    t0_signals = _signals(scan, "t0")
    t1_signals = _signals(scan, "t1")
    decision = _decision_payload(snapshot, lead_id)
    return {
        "id": lead_id,
        "domain": lead.normalized_domain,
        "normalized_domain": lead.normalized_domain,
        "company": lead.company_name,
        "nip": lead.nip,
        "source": lead.source,
        "status": lead.status,
        "t0_score": t0_signals.get("t0_score"),
        "t0_signals": t0_signals,
        "t0_5_signals": _signals(scan, "t0_5"),
        "t1_signals": t1_signals,
        "decision": decision,
    }


@router.get("")
def list_leads(
    status: str | None = None,
    source: str | None = None,
    action: str | None = None,
    campaign: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    store: StateStore = Depends(get_state_store),
) -> dict[str, Any]:
    snapshot = store.load_snapshot()
    rows = [_lead_row(lead, snapshot) for lead in snapshot.leads]
    if status:
        rows = [row for row in rows if row["status"] == status]
    if source:
        rows = [row for row in rows if row["source"] == source]
    if action:
        rows = [row for row in rows if (row["decision"] or {}).get("action") == action]
    if campaign:
        rows = [row for row in rows if (row["decision"] or {}).get("campaign") == campaign]
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": rows[start : start + page_size], "total": total, "page": page, "page_size": page_size}


@router.get("/{lead_id}")
def get_lead(lead_id: str, store: StateStore = Depends(get_state_store)) -> dict[str, Any]:
    snapshot = store.load_snapshot()
    lead = next((item for item in snapshot.leads if str(item.id) == lead_id), None)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return {
        "lead": lead.model_dump(mode="json"),
        "scans": snapshot.scans.get(lead_id) or {},
        "decision": _decision_payload(snapshot, lead_id),
        "trace": _trace_payload(snapshot, lead_id),
    }
