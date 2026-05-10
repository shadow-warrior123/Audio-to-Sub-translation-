from __future__ import annotations

import logging
import uuid
from pathlib import Path

from app.core.config import Settings
from app.jobs.store import JobStore
from app.pipeline.processor import process_video

logger = logging.getLogger(__name__)


def new_job_id() -> str:
    return uuid.uuid4().hex


def run_job(job_id: str, video_path: Path, store: JobStore, settings: Settings) -> None:
    logger.info("Starting job %s for %s", job_id, video_path)
    store.update(job_id, status="running", progress=1, step="starting")

    def progress(percent: int, step: str) -> None:
        store.update(job_id, status="running", progress=percent, step=step)

    try:
        outputs = process_video(
            video_path=video_path,
            output_dir=settings.output_dir,
            settings=settings,
            job_id=job_id,
            progress=progress,
        )
        store.update(
            job_id,
            status="completed",
            progress=100,
            step="completed",
            subtitle_path=outputs.subtitle_path,
            video_path=outputs.rendered_video_path,
            audio_path=outputs.audio_path,
            segment_count=outputs.segment_count,
        )
    except Exception as exc:
        logger.exception("Job %s failed", job_id)
        store.update(job_id, status="failed", step="failed", error=str(exc))

