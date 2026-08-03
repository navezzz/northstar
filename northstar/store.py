from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from northstar.models import Decision


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    error TEXT
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    ticker TEXT NOT NULL,
                    as_of TEXT NOT NULL,
                    score REAL NOT NULL,
                    payload TEXT NOT NULL,
                    PRIMARY KEY (run_id, ticker)
                );
                """
            )

    def save_completed_run(self, decisions: list[Decision]) -> str:
        run_id = uuid.uuid4().hex
        now = datetime.now(UTC).isoformat()
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO runs(id, started_at, completed_at, status) VALUES (?, ?, ?, 'complete')",
                (run_id, now, now),
            )
            connection.executemany(
                "INSERT INTO decisions(run_id, ticker, as_of, score, payload) VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        run_id,
                        decision.ticker,
                        decision.as_of,
                        decision.score,
                        json.dumps(decision.to_dict()),
                    )
                    for decision in decisions
                ],
            )
        return run_id

    def latest(self) -> dict | None:
        with self.connect() as connection:
            run = connection.execute(
                "SELECT * FROM runs WHERE status = 'complete' ORDER BY completed_at DESC LIMIT 1"
            ).fetchone()
            if run is None:
                return None
            rows = connection.execute(
                "SELECT payload FROM decisions WHERE run_id = ? ORDER BY score DESC, ticker",
                (run["id"],),
            ).fetchall()
        return {
            "run_id": run["id"],
            "completed_at": run["completed_at"],
            "decisions": [json.loads(row["payload"]) for row in rows],
        }
