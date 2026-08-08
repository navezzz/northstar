from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from northstar.config import Settings
from northstar.store import Store

settings = Settings.from_env()
store = Store(settings.db_path)
web_dir = Path(__file__).parent / "web"

app = FastAPI(title="Northstar API", version="0.1.0")
app.mount("/assets", StaticFiles(directory=web_dir), name="assets")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/decisions/latest")
def latest_decisions() -> dict:
    result = store.latest_snapshot() or store.latest()
    if result is None:
        raise HTTPException(status_code=404, detail="No completed daily run yet")
    return result


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(web_dir / "index.html")
