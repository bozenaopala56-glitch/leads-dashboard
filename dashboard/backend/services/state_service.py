from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from leadpipe.models import Lead


def empty_state() -> dict[str, Any]:
    return {"leads": [], "scans": {}, "decisions": {}}


@dataclass(frozen=True)
class StateSnapshot:
    leads: list[Lead]
    scans: dict[str, Any]
    decisions: dict[str, Any]
    raw: dict[str, Any]
    errors: list[str]


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_state(self) -> dict[str, Any]:
        if not self.path.exists():
            return empty_state()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return empty_state()
        if not isinstance(payload, dict):
            return empty_state()
        leads = payload.get("leads", [])
        scans = payload.get("scans", {})
        decisions = payload.get("decisions", {})
        return {
            "leads": leads if isinstance(leads, list) else [],
            "scans": scans if isinstance(scans, dict) else {},
            "decisions": decisions if isinstance(decisions, dict) else {},
        }

    def save_state(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temp_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        temp_path.replace(self.path)

    def load_snapshot(self) -> StateSnapshot:
        raw = self.load_state()
        leads: list[Lead] = []
        errors: list[str] = []
        for index, item in enumerate(raw["leads"]):
            try:
                leads.append(Lead.model_validate(item))
            except ValueError as exc:
                errors.append(f"leads[{index}]: {exc}")
        return StateSnapshot(
            leads=leads,
            scans=raw["scans"],
            decisions=raw["decisions"],
            raw=raw,
            errors=errors,
        )
