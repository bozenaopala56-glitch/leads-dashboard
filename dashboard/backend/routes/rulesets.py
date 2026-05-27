from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/rulesets", tags=["rulesets"])
logger = logging.getLogger(__name__)


def rules_dir() -> Path:
    # Prefer LEADPIPE_RULES env var; fallback to leadpipe package rules/ directory
    env_path = os.environ.get("LEADPIPE_RULES")
    if env_path:
        return Path(env_path)
    try:
        import leadpipe as _lp
        return Path(_lp.__file__).resolve().parent / "rules"
    except Exception:
        return Path("leadpipe/rules")


def _safe_rules_dir() -> Path:
    return rules_dir().resolve()


def _safe_ruleset_path(name: str) -> Path:
    if Path(name).name != name or not name.endswith((".yml", ".yaml")):
        raise HTTPException(status_code=404, detail="ruleset not found")
    directory = _safe_rules_dir()
    path = (directory / name).resolve()
    if not path.is_relative_to(directory):
        logger.warning("blocked ruleset path outside directory: %s", name)
        raise HTTPException(status_code=404, detail="ruleset not found")
    return path


@router.get("")
def list_rulesets() -> dict[str, Any]:
    directory = _safe_rules_dir()
    if not directory.exists():
        return {"items": [], "total": 0}
    items = []
    try:
        candidates = sorted([*directory.glob("*.yml"), *directory.glob("*.yaml")])
        for path in candidates:
            resolved = path.resolve()
            if not resolved.is_relative_to(directory) or not resolved.is_file():
                continue
            items.append(
                {
                    "name": path.name,
                    "size": resolved.stat().st_size,
                }
            )
    except OSError:
        logger.exception("failed to list rulesets in %s", directory)
        raise HTTPException(status_code=500, detail="failed to list rulesets") from None
    return {"items": items, "total": len(items)}


@router.get("/{name}")
def get_ruleset(name: str) -> dict[str, str]:
    path = _safe_ruleset_path(name)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="ruleset not found")
    try:
        return {"name": path.name, "content": path.read_text(encoding="utf-8")}
    except OSError:
        logger.exception("failed to read ruleset %s", path)
        raise HTTPException(status_code=500, detail="failed to read ruleset") from None
