from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..deps import get_state_store
from ..services.state_service import StateStore

router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("")
def list_decisions(store: StateStore = Depends(get_state_store)) -> dict[str, Any]:
    snapshot = store.load_snapshot()
    leads_by_id = {str(lead.id): lead for lead in snapshot.leads}
    items = []
    for lead_id, entry in snapshot.decisions.items():
        if not isinstance(entry, dict):
            continue
        lead = leads_by_id.get(lead_id)
        items.append(
            {
                "lead_id": lead_id,
                "domain": lead.normalized_domain if lead else None,
                "company": lead.company_name if lead else None,
                "decision": entry.get("decision"),
                "trace": entry.get("trace"),
            }
        )
    items.sort(key=lambda item: item["lead_id"])
    return {"items": items, "total": len(items)}
