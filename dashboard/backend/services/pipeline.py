from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from leadpipe.csv_schemas import ImportCsvSchema, parse_csv


class PipelineService:
    def validate_import_csv(self, path: Path) -> None:
        _, errors = parse_csv(path, ImportCsvSchema)
        if errors:
            detail = [{"row": row, "errors": messages} for row, messages in errors]
            raise HTTPException(status_code=422, detail=detail)

    async def persist_upload(self, upload: UploadFile) -> Path:
        suffix = Path(upload.filename or "leads.csv").suffix or ".csv"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(await upload.read())
            return Path(handle.name)

    def import_csv(self, path: Path) -> dict[str, Any]:
        self.validate_import_csv(path)
        from leadpipe import cli

        exit_code = cli.command_import(argparse.Namespace(file=str(path)))
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=f"leadpipe import failed with exit code {exit_code}")
        return {"imported": True}
