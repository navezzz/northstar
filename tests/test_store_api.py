from fastapi.testclient import TestClient

from northstar.config import Settings
from northstar.demo import DemoProvider
from northstar.pipeline import run_daily
from northstar.store import Store


def test_completed_run_is_read_atomically(tmp_path):
    settings = Settings(tmp_path / "northstar.db", ("AAPL", "MSFT"), 100_000, 0.005)
    store = Store(settings.db_path)
    run_id, decisions = run_daily(DemoProvider(), store, settings)
    latest = store.latest()
    assert latest["run_id"] == run_id
    assert len(latest["decisions"]) == len(decisions) == 2


def test_api_health():
    from northstar.api import app

    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
