from __future__ import annotations

import json
import shutil
from pathlib import Path


def export_site(snapshot: dict, destination: Path) -> Path:
    """Build a self-contained static dashboard directory."""
    web_dir = Path(__file__).parent / "web"
    assets_dir = destination / "assets"
    data_dir = destination / "data"
    assets_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(web_dir / "index.html", destination / "index.html")
    shutil.copy2(web_dir / "styles.css", assets_dir / "styles.css")
    shutil.copy2(web_dir / "app.js", assets_dir / "app.js")
    (destination / ".nojekyll").write_text("", encoding="utf-8")
    latest_path = data_dir / "latest.json"
    latest_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return destination
