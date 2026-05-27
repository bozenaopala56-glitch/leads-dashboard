from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile, status

from ..deps import get_state_store
from ..services.pipeline import PipelineService
from ..services.state_service import StateStore

router = APIRouter(prefix="/api/batches", tags=["batches"])


def _batch_id_for(lead: Any) -> str:
    return str(lead.batch_id) if lead.batch_id else "default"


@router.get("")
def list_batches(store: StateStore = Depends(get_state_store)) -> dict[str, list[dict[str, Any]]]:
    snapshot = store.load_snapshot()
    grouped: dict[str, list[Any]] = defaultdict(list)
    for lead in snapshot.leads:
        grouped[_batch_id_for(lead)].append(lead)

    items = []
    for batch_id, leads in grouped.items():
        status_counts = Counter(str(lead.status) for lead in leads)
        sources = sorted({lead.source for lead in leads if lead.source})
        items.append(
            {
                "id": batch_id,
                "source": sources[0] if sources else None,
                "lead_count": len(leads),
                "status_counts": dict(status_counts),
            }
        )
    items.sort(key=lambda item: item["id"])
    return {"items": items}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_batch(
    file: UploadFile = File(...),
    store: StateStore = Depends(get_state_store),
) -> dict[str, Any]:
    service = PipelineService()
    path = await service.persist_upload(file)
    try:
        result = service.import_csv(path)
    finally:
        Path(path).unlink(missing_ok=True)
    return {**result, "state": store.load_state()}
