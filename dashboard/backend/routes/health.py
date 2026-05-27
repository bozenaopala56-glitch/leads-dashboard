from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import get_state_store
from ..services.state_service import StateStore

router = APIRouter()


@router.get("/api/health")
@router.get("/health")
def health(store: StateStore = Depends(get_state_store)) -> dict[str, object]:
    return {"status": "ok", "state_configured": bool(store.path)}
