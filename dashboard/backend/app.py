from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI

LEADPIPE_ROOT = Path("/tmp/leadpipe-t0")
if LEADPIPE_ROOT.exists() and str(LEADPIPE_ROOT) not in sys.path:
    sys.path.insert(0, str(LEADPIPE_ROOT))

from .routes import batches, health


app = FastAPI(title="leadpipe dashboard", version="0.1.0")
app.include_router(health.router)
app.include_router(batches.router)
