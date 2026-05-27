from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/rulesets", tags=["rulesets"])


def rules_dir() -> Path:
    return Path(os.environ.get("LEADPIPE_RULES", "/tmp/leadpipe-t0/leadpipe/rules"))


@router.get("")
def list_rulesets() -> dict[str, list[dict[str, Any]]]:
    directory = rules_dir()
    if not directory.exists():
        return {"items": []}
    items = [
        {
            "name": path.name,
            "size": path.stat().st_size,
        }
        for path in sorted(directory.glob("*.yml"))
        if path.is_file()
    ]
    return {"items": items}


@router.get("/{name}")
def get_ruleset(name: str) -> dict[str, str]:
    if "/" in name or "\\" in name or not name.endswith((".yml", ".yaml")):
        raise HTTPException(status_code=404, detail="ruleset not found")
    path = rules_dir() / name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="ruleset not found")
    return {"name": path.name, "content": path.read_text(encoding="utf-8")}
