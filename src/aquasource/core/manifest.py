"""Idempotent manifest.

State lives in SQLite (one row per sample_id, upserted), so re-running never
duplicates rows and completed downloads are skipped. ``export()`` writes the
human-facing ``samples.jsonl`` from that state, sorted by sample_id.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterator


class Manifest:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS samples ("
            " sample_id TEXT PRIMARY KEY,"
            " status TEXT NOT NULL,"
            " local_path TEXT,"
            " bytes INTEGER,"
            " row TEXT NOT NULL)"
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def __enter__(self) -> "Manifest":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get(self, sample_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT row FROM samples WHERE sample_id = ?", (sample_id,))
        hit = cur.fetchone()
        return json.loads(hit[0]) if hit else None

    def is_complete(self, sample_id: str, root: Path | None = None) -> bool:
        """Downloaded earlier and the file is still there with the recorded size."""
        cur = self.conn.execute(
            "SELECT status, local_path, bytes FROM samples WHERE sample_id = ?", (sample_id,)
        )
        hit = cur.fetchone()
        if not hit or hit[0] != "downloaded" or not hit[1]:
            return False
        path = Path(hit[1])
        if not path.is_absolute() and root is not None:
            path = root / path
        try:
            return hit[2] is None or path.stat().st_size == hit[2]
        except OSError:
            return False

    def upsert(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO samples (sample_id, status, local_path, bytes, row) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(sample_id) DO UPDATE SET status=excluded.status,"
            " local_path=excluded.local_path, bytes=excluded.bytes, row=excluded.row",
            (row["sample_id"], row["status"], row.get("local_path"), row.get("bytes"), json.dumps(row)),
        )

    def commit(self) -> None:
        self.conn.commit()

    def rows(self, status: str | None = None) -> Iterator[dict[str, Any]]:
        if status is None:
            cur = self.conn.execute("SELECT row FROM samples ORDER BY sample_id")
        else:
            cur = self.conn.execute("SELECT row FROM samples WHERE status = ? ORDER BY sample_id", (status,))
        for (row,) in cur:
            yield json.loads(row)

    def count(self, status: str | None = None) -> int:
        if status is None:
            return self.conn.execute("SELECT COUNT(*) FROM samples").fetchone()[0]
        return self.conn.execute("SELECT COUNT(*) FROM samples WHERE status = ?", (status,)).fetchone()[0]

    def export(self, path: Path, status: str | None = "downloaded") -> int:
        """Write rows (default: downloaded ones) to JSONL atomically. Returns the row count."""
        self.commit()
        tmp = Path(str(path) + ".tmp")
        n = 0
        with open(tmp, "w", encoding="utf-8") as fh:
            for row in self.rows(status):
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
        os.replace(tmp, path)
        return n


class JsonlLog:
    """Append-only JSONL writer that drops exact duplicate lines already present."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seen: set[str] = set()
        if self.path.exists():
            with open(self.path, encoding="utf-8") as fh:
                self._seen.update(line.rstrip("\n") for line in fh)

    def write(self, entry: dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        if line in self._seen:
            return
        self._seen.add(line)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
