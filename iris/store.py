"""SQLite state: assets, jobs, downloads. WAL mode, one writer, a file lock around heavy jobs.

The VM is shared between bots; the lock prevents two analyses from running at once and a job key makes
repeated requests idempotent."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from . import paths

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  sha256 TEXT NOT NULL UNIQUE,
  bytes INTEGER NOT NULL,
  source_kind TEXT NOT NULL,
  source_url TEXT,
  source_path TEXT,
  rights TEXT NOT NULL,
  readable INTEGER NOT NULL,
  manifest_path TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  job_key TEXT NOT NULL UNIQUE,
  asset_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  mode TEXT,
  state TEXT NOT NULL,
  stages_done TEXT NOT NULL DEFAULT '[]',
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS downloads (
  ts TEXT NOT NULL,
  url TEXT NOT NULL,
  ok INTEGER NOT NULL,
  note TEXT
);
CREATE TABLE IF NOT EXISTS counters (
  name TEXT PRIMARY KEY,
  value INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS claims (
  claim_id TEXT PRIMARY KEY,
  claim_key TEXT NOT NULL UNIQUE,
  asset_id TEXT NOT NULL,
  dimension TEXT NOT NULL,
  term_id TEXT NOT NULL,
  source TEXT NOT NULL,
  claim_kind TEXT NOT NULL,
  review_status TEXT NOT NULL,
  corrected_term_id TEXT,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS claims_asset ON claims(asset_id);
CREATE TABLE IF NOT EXISTS review_events (
  ts TEXT NOT NULL,
  claim_id TEXT NOT NULL,
  status TEXT NOT NULL,
  value TEXT,
  reason TEXT,
  author TEXT NOT NULL
);
"""

JOB_STATES = (
    "created", "indexed", "measuring", "interpreting_grok", "interpreting_anthropic",
    "review_ready", "reviewed", "built", "partial", "needs_input", "failed", "canceled",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def job_key(parts: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Store:
    def __init__(self, workspace: Path | None = None) -> None:
        self.workspace = workspace or paths.workspace_root()
        self.db_dir = self.workspace / "db"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.db_dir / "iris.sqlite"
        self.lock_path = self.db_dir / ".lock"
        self.conn = sqlite3.connect(str(self.db_path), timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # ---- lock -------------------------------------------------------------------------------
    @contextlib.contextmanager
    def heavy_job_lock(self, wait_s: float = 0.0) -> Iterator[None]:
        """Exclusive lock for heavy work. Raises BlockingIOError if another job holds it."""
        fh = self.lock_path.open("a+")
        deadline = time.time() + wait_s
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() >= deadline:
                    fh.close()
                    raise
                time.sleep(0.2)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            fh.close()

    # ---- assets -----------------------------------------------------------------------------
    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
        return dict(row) if row else None

    def get_asset_by_sha(self, sha: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM assets WHERE sha256=?", (sha,)).fetchone()
        return dict(row) if row else None

    def insert_asset(self, rec: dict[str, Any]) -> None:
        cols = ",".join(rec.keys())
        qs = ",".join("?" for _ in rec)
        with self.conn:
            self.conn.execute(f"INSERT INTO assets ({cols}) VALUES ({qs})", tuple(rec.values()))

    # ---- downloads --------------------------------------------------------------------------
    def record_download(self, url: str, ok: bool, note: str | None = None) -> None:
        with self.conn:
            self.conn.execute("INSERT INTO downloads (ts,url,ok,note) VALUES (?,?,?,?)", (now_iso(), url, int(ok), note))

    def downloads_last_24h(self) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - 86400
        rows = self.conn.execute("SELECT ts FROM downloads").fetchall()
        return sum(1 for r in rows if datetime.fromisoformat(r["ts"]).timestamp() >= cutoff)

    def seconds_since_last_download(self) -> float | None:
        row = self.conn.execute("SELECT ts FROM downloads ORDER BY ts DESC LIMIT 1").fetchone()
        if not row:
            return None
        return datetime.now(timezone.utc).timestamp() - datetime.fromisoformat(row["ts"]).timestamp()

    # ---- jobs -------------------------------------------------------------------------------
    def get_job(self, job_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return self._job(row)

    def get_job_by_key(self, key: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE job_key=?", (key,)).fetchone()
        return self._job(row)

    def create_or_get_job(self, key: str, asset_id: str, kind: str, mode: str | None) -> tuple[dict[str, Any], bool]:
        """Returns (job, created). A second call with the same key returns the existing job."""
        existing = self.get_job_by_key(key)
        if existing:
            return existing, False
        job_id = "job_" + uuid.uuid4().hex[:12]
        ts = now_iso()
        with self.conn:
            self.conn.execute(
                "INSERT INTO jobs (job_id,job_key,asset_id,kind,mode,state,stages_done,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (job_id, key, asset_id, kind, mode, "created", "[]", ts, ts),
            )
        return self.get_job(job_id), True  # type: ignore[return-value]

    def update_job(self, job_id: str, *, state: str | None = None, stage_done: str | None = None, error: str | None = None) -> dict[str, Any]:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(job_id)
        stages = list(job["stages_done"])
        if stage_done and stage_done not in stages:
            stages.append(stage_done)
        new_state = state or job["state"]
        if new_state not in JOB_STATES:
            raise ValueError(f"unknown job state {new_state}")
        with self.conn:
            self.conn.execute(
                "UPDATE jobs SET state=?, stages_done=?, error=?, updated_at=? WHERE job_id=?",
                (new_state, json.dumps(stages), error if error is not None else job["error"], now_iso(), job_id),
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def list_jobs(self, asset_id: str | None = None) -> list[dict[str, Any]]:
        if asset_id:
            rows = self.conn.execute("SELECT * FROM jobs WHERE asset_id=? ORDER BY created_at", (asset_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
        return [self._job(r) for r in rows if r]  # type: ignore[misc]

    @staticmethod
    def _job(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        d = dict(row)
        d["stages_done"] = json.loads(d.get("stages_done") or "[]")
        return d

    # ---- claims -----------------------------------------------------------------------------
    def next_claim_ids(self, n: int) -> list[str]:
        with self.conn:
            row = self.conn.execute("SELECT value FROM counters WHERE name='claim'").fetchone()
            start = int(row["value"]) if row else 0
            self.conn.execute("INSERT OR REPLACE INTO counters (name,value) VALUES ('claim',?)", (start + n,))
        return [f"c_{i:06d}" for i in range(start + 1, start + n + 1)]

    def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT body FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        return json.loads(row["body"]) if row else None

    def get_claim_by_key(self, key: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT body FROM claims WHERE claim_key=?", (key,)).fetchone()
        return json.loads(row["body"]) if row else None

    def upsert_claim(self, claim: dict[str, Any]) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO claims (claim_id,claim_key,asset_id,dimension,term_id,source,claim_kind,review_status,corrected_term_id,body,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(claim_id) DO UPDATE SET review_status=excluded.review_status, "
                "corrected_term_id=excluded.corrected_term_id, body=excluded.body, updated_at=excluded.updated_at",
                (claim["claim_id"], claim["claim_key"], claim["asset_id"], claim["dimension"], claim["term_id"], claim["source"],
                 claim["claim_kind"], claim["review_status"], claim.get("corrected_term_id"), json.dumps(claim, ensure_ascii=False),
                 claim.get("created_at") or now_iso(), claim.get("updated_at") or now_iso()),
            )

    def list_claims(self, asset_id: str | None = None) -> list[dict[str, Any]]:
        if asset_id:
            rows = self.conn.execute("SELECT body FROM claims WHERE asset_id=? ORDER BY claim_id", (asset_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT body FROM claims ORDER BY claim_id").fetchall()
        return [json.loads(r["body"]) for r in rows]

    def add_review_event(self, claim_id: str, status: str, author: str, value: str | None = None, reason: str | None = None) -> dict[str, Any]:
        ev = {"ts": now_iso(), "claim_id": claim_id, "status": status, "value": value, "reason": reason, "author": author}
        with self.conn:
            self.conn.execute("INSERT INTO review_events (ts,claim_id,status,value,reason,author) VALUES (?,?,?,?,?,?)",
                              (ev["ts"], claim_id, status, value, reason, author))
        return ev

    def review_events(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        if claim_id:
            rows = self.conn.execute("SELECT * FROM review_events WHERE claim_id=? ORDER BY ts", (claim_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM review_events ORDER BY ts").fetchall()
        return [dict(r) for r in rows]
