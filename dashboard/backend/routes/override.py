from __future__ import annotations

from datetime import timezone
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from leadpipe.models import CampaignKey, DecisionAction, utcnow
from pydantic import BaseModel, Field, model_validator

from ..deps import get_state_store
from ..services.state_service import StateStore

router = APIRouter(prefix="/api/leads", tags=["override"])
logger = logging.getLogger(__name__)


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
    def apply_override(state: dict[str, Any]) -> dict[str, Any]:
        lead_exists = any(isinstance(item, dict) and str(item.get("id")) == lead_id for item in state["leads"])
        if not lead_exists:
            raise HTTPException(status_code=404, detail="lead not found")

        entry = state["decisions"].setdefault(lead_id, {})
        if not isinstance(entry, dict):
            logger.error("decision entry for lead %s is not an object; replacing malformed entry", lead_id)
            entry = {}
            state["decisions"][lead_id] = entry
        decision = entry.setdefault("decision", {})
        if not isinstance(decision, dict):
            logger.error("decision payload for lead %s is not an object; replacing malformed decision", lead_id)
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
            "action": payload.action.value,
            "campaign": payload.campaign.value if payload.campaign else None,
            "reason": payload.reason,
        }
        history = metadata.setdefault("dashboard_override_audit", [])
        if not isinstance(history, list):
            history = []
            metadata["dashboard_override_audit"] = history
        history.append(audit)
        metadata["dashboard_override"] = audit

        decision["action"] = payload.action.value
        decision["campaign"] = payload.campaign.value if payload.campaign else None
        return decision

    decision = store.update_state(apply_override)
    return {"lead_id": lead_id, "decision": decision}
