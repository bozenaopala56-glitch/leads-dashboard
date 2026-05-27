from __future__ import annotations

import json
import logging
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

import fcntl

from leadpipe.models import Lead

logger = logging.getLogger(__name__)
T = TypeVar("T")


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
        self.lock_path = path.with_suffix(f"{path.suffix}.lock")

    @contextmanager
    def _locked(self, operation: int) -> Iterator[None]:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            with os.fdopen(fd, "r+") as handle:
                fcntl.flock(handle.fileno(), operation)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            logger.exception("state lock failed for %s", self.path)
            raise

    def load_state(self) -> dict[str, Any]:
        with self._locked(fcntl.LOCK_SH):
            return self._load_state_unlocked()

    def _load_state_unlocked(self) -> dict[str, Any]:
        if not self.path.exists():
            return empty_state()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except OSError:
            logger.exception("failed to read state file %s", self.path)
            return empty_state()
        except json.JSONDecodeError:
            logger.exception("invalid JSON in state file %s", self.path)
            return empty_state()
        if not isinstance(payload, dict):
            logger.error("state file %s has invalid root type: %s", self.path, type(payload).__name__)
            return empty_state()
        leads = payload.get("leads", [])
        scans = payload.get("scans", {})
        decisions = payload.get("decisions", {})
        if not isinstance(leads, list) or not isinstance(scans, dict) or not isinstance(decisions, dict):
            logger.error("state file %s has invalid section types", self.path)
        return {
            "leads": leads if isinstance(leads, list) else [],
            "scans": scans if isinstance(scans, dict) else {},
            "decisions": decisions if isinstance(decisions, dict) else {},
        }

    def save_state(self, state: dict[str, Any]) -> None:
        with self._locked(fcntl.LOCK_EX):
            self._save_state_unlocked(state)

    def _save_state_unlocked(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temp_path.replace(self.path)
        except OSError:
            logger.exception("failed to write state file %s", self.path)
            raise
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def update_state(self, mutator: Callable[[dict[str, Any]], T]) -> T:
        with self._locked(fcntl.LOCK_EX):
            state = self._load_state_unlocked()
            result = mutator(state)
            self._save_state_unlocked(state)
            return result

    def load_snapshot(self) -> StateSnapshot:
        raw = self.load_state()
        leads: list[Lead] = []
        errors: list[str] = []
        for index, item in enumerate(raw["leads"]):
            try:
                leads.append(Lead.model_validate(item))
            except ValueError as exc:
                logger.exception("invalid lead in state file %s at index %s", self.path, index)
                errors.append(f"leads[{index}]: {exc}")
        return StateSnapshot(
            leads=leads,
            scans=raw["scans"],
            decisions=raw["decisions"],
            raw=raw,
            errors=errors,
        )
