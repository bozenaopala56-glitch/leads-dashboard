from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from leadpipe.csv_schemas import ExportCsvSchema, dump_csv

from ..deps import get_state_store
from ..services.state_service import StateStore

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("")
def export_csv(store: StateStore = Depends(get_state_store)) -> Response:
    snapshot = store.load_snapshot()
    leads_by_id = {str(lead.id): lead for lead in snapshot.leads}
    records: list[ExportCsvSchema] = []
    for lead_id, entry in snapshot.decisions.items():
        if not isinstance(entry, dict):
            continue
        decision = entry.get("decision") or {}
        if decision.get("action") != "send":
            continue
        lead = leads_by_id.get(lead_id)
        if not lead:
            continue
        records.append(
            ExportCsvSchema(
                firma=lead.company_name,
                domena=lead.normalized_domain,
                email=lead.contact_email,
                telefon=lead.phone,
                kampania=decision.get("campaign"),
                subject=decision.get("subject"),
                confidence=decision.get("confidence") or 0,
            )
        )
    return Response(content=dump_csv(records), media_type="text/csv")
