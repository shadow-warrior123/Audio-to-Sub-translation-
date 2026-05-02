from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class JobRecord:
    id: str
    status: str
    progress: int
    step: str
    input_path: str
    subtitle_path: str | None
    video_path: str | None
    audio_path: str | None
    segment_count: int | None
    error: str | None
    logs: list[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class JobStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL,
                    step TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    subtitle_path TEXT,
                    video_path TEXT,
                    audio_path TEXT,
                    segment_count INTEGER,
                    error TEXT,
                    logs TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create(self, job_id: str, input_path: str) -> JobRecord:
        now = utc_now()
        record = JobRecord(
            id=job_id,
            status="queued",
            progress=0,
            step="queued",
            input_path=input_path,
            subtitle_path=None,
            video_path=None,
            audio_path=None,
            segment_count=None,
            error=None,
            logs=["queued"],
            created_at=now,
            updated_at=now,
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs VALUES (
                    :id, :status, :progress, :step, :input_path, :subtitle_path,
                    :video_path, :audio_path, :segment_count, :error, :logs,
                    :created_at, :updated_at
                )
                """,
                _serialize(record),
            )
        return record

    def update(self, job_id: str, **fields: Any) -> JobRecord:
        existing = self.get(job_id)
        if existing is None:
            raise KeyError(f"Unknown job id: {job_id}")
        data = existing.to_dict()
        logs = list(data["logs"])
        if "step" in fields and fields["step"] != data["step"]:
            logs.append(str(fields["step"]))
        if "error" in fields and fields["error"]:
            logs.append(str(fields["error"]))
        data.update(fields)
        data["logs"] = logs
        data["updated_at"] = utc_now()
        columns = [
            "status",
            "progress",
            "step",
            "input_path",
            "subtitle_path",
            "video_path",
            "audio_path",
            "segment_count",
            "error",
            "logs",
            "updated_at",
        ]
        assignments = ", ".join(f"{column} = :{column}" for column in columns)
        data["id"] = job_id
        with self._lock, self._connect() as connection:
            connection.execute(f"UPDATE jobs SET {assignments} WHERE id = :id", _serialize_dict(data))
        updated = self.get(job_id)
        if updated is None:
            raise KeyError(f"Unknown job id after update: {job_id}")
        return updated

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list_recent(self, limit: int = 50) -> list[JobRecord]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def mark_active_jobs_interrupted(self) -> int:
        now = utc_now()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE jobs
                SET status = 'failed',
                    step = 'interrupted',
                    error = 'Job was interrupted by an application restart.',
                    logs = json_insert(logs, '$[#]', 'interrupted by application restart'),
                    updated_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (now,),
            )
            return cursor.rowcount


def _serialize(record: JobRecord) -> dict[str, Any]:
    return _serialize_dict(record.to_dict())


def _serialize_dict(data: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(data)
    serialized["logs"] = json.dumps(serialized["logs"], ensure_ascii=False)
    return serialized


def _row_to_record(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=row["id"],
        status=row["status"],
        progress=row["progress"],
        step=row["step"],
        input_path=row["input_path"],
        subtitle_path=row["subtitle_path"],
        video_path=row["video_path"],
        audio_path=row["audio_path"],
        segment_count=row["segment_count"],
        error=row["error"],
        logs=json.loads(row["logs"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
