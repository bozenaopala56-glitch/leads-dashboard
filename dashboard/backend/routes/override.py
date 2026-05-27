from __future__ import annotations

from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from leadpipe.models import CampaignKey, DecisionAction, utcnow
from pydantic import BaseModel, Field, model_validator

from ..deps import get_state_store
from ..services.state_service import StateStore

router = APIRouter(prefix="/api/leads", tags=["override"])


class OverrideRequest(BaseModel):
    action: DecisionAction
    campaign: CampaignKey | None = None
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def send_requires_campaign(self) -> "OverrideRequest":
        if self.action == DecisionAction.SEND and self.campaign is None:
            raise ValueError("send override requires campaign")
        return self


@router.post("/{lead_id}/override")
def override_lead(
    lead_id: str,
    payload: OverrideRequest,
    remote_user: str | None = Header(default=None, alias="Remote-User"),
    store: StateStore = Depends(get_state_store),
) -> dict[str, Any]:
    state = store.load_state()
    lead_exists = any(isinstance(item, dict) and item.get("id") == lead_id for item in state["leads"])
    if not lead_exists:
        raise HTTPException(status_code=404, detail="lead not found")

    entry = state["decisions"].setdefault(lead_id, {})
    if not isinstance(entry, dict):
        entry = {}
        state["decisions"][lead_id] = entry
    decision = entry.setdefault("decision", {})
    if not isinstance(decision, dict):
        decision = {}
        entry["decision"] = decision

    metadata = decision.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        decision["metadata"] = metadata

    audit = {
        "actor": remote_user or "unknown",
        "at": utcnow().astimezone(timezone.utc).isoformat(),
        "previous_action": decision.get("action"),
        "previous_campaign": decision.get("campaign"),
        "action": payload.action,
        "campaign": payload.campaign,
        "reason": payload.reason,
    }
    history = metadata.setdefault("dashboard_override_audit", [])
    if isinstance(history, list):
        history.append(audit)
    metadata["dashboard_override"] = audit

    store.save_state(state)
    return {"lead_id": lead_id, "decision": decision}
