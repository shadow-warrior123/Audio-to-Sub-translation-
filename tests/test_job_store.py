from pathlib import Path
from uuid import uuid4

from app.jobs.store import JobStore


def test_job_store_persists_records():
    temp_dir = Path("data/test") / f"anime_subtitle_test_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    database = temp_dir / "jobs.sqlite3"
    store = JobStore(database)

    store.create("job-1", "input.mp4")
    store.update("job-1", status="completed", progress=100, step="completed")

    reloaded = JobStore(database)
    record = reloaded.get("job-1")

    assert record is not None
    assert record.status == "completed"
    assert record.progress == 100


def test_job_store_marks_active_jobs_interrupted():
    temp_dir = Path("data/test") / f"anime_subtitle_test_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    store = JobStore(temp_dir / "jobs.sqlite3")
    store.create("job-1", "input.mp4")
    store.update("job-1", status="running", progress=20, step="transcribing_japanese")

    count = store.mark_active_jobs_interrupted()
    record = store.get("job-1")

    assert count == 1
    assert record is not None
    assert record.status == "failed"
    assert record.step == "interrupted"
