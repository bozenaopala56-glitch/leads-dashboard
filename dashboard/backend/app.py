from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

LEADPIPE_ROOT = Path(os.environ.get("LEADPIPE_ROOT", "/tmp/leadpipe-t0"))
if LEADPIPE_ROOT.exists() and str(LEADPIPE_ROOT) not in sys.path:
    sys.path.insert(0, str(LEADPIPE_ROOT))
DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))

from backend.routes import batches, decisions, export, health, leads, override, rulesets


app = FastAPI(title="leadpipe dashboard", version="0.1.0")
app.include_router(health.router)
app.include_router(batches.router)
app.include_router(override.router)
app.include_router(leads.router)
app.include_router(decisions.router)
app.include_router(export.router)
app.include_router(rulesets.router)

FRONTEND_DIR = DASHBOARD_ROOT / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
