from __future__ import annotations

import os
from pathlib import Path

from .services.state_service import StateStore


def get_state_path() -> Path:
    return Path(os.environ.get("LEADPIPE_STATE", ".leadpipe/state.json"))


def get_state_store() -> StateStore:
    return StateStore(get_state_path())
