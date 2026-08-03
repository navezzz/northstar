import json

from northstar.site_export import export_site


def test_export_site_contains_assets_and_snapshot(tmp_path):
    snapshot = {"run_id": "abc", "completed_at": "2026-08-02T00:00:00Z", "decisions": []}
    destination = export_site(snapshot, tmp_path / "site")

    assert (destination / "index.html").exists()
    assert (destination / "assets" / "app.js").exists()
    assert (destination / ".nojekyll").exists()
    assert json.loads((destination / "data" / "latest.json").read_text()) == snapshot
