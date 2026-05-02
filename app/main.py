from __future__ import annotations

from dataclasses import replace
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import TRANSLATION_MODEL_OPTIONS, WHISPER_MODEL_OPTIONS, Settings, settings
from app.core.logging import configure_logging
from app.jobs.runner import new_job_id, run_job
from app.jobs.store import JobStore
from app.pipeline.ffmpeg import ffmpeg_available

configure_logging()
settings.ensure_directories()
store = JobStore(settings.database_path)
store.mark_active_jobs_interrupted()

app = FastAPI(title=settings.app_name, version="1.0.0")

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=STATIC_DIR, html=True), name="desktop-ui")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "ffmpeg": ffmpeg_available(settings),
        "whisper_model_size": settings.whisper_model_size,
        "whisper_device": settings.whisper_device,
        "whisper_compute_type": settings.whisper_compute_type,
        "translation_model": settings.translation_model,
        "translation_device": settings.translation_device,
        "model_options": {
            "whisper": list(WHISPER_MODEL_OPTIONS),
            "translation": list(TRANSLATION_MODEL_OPTIONS),
        },
    }


@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    whisper_model_size: str = Form(default=settings.whisper_model_size),
    translation_model: str = Form(default=settings.translation_model),
) -> dict[str, object]:
    job_settings = _settings_for_job(whisper_model_size, translation_model)
    job_id, saved_path = await _save_upload(file)
    record = store.create(job_id, str(saved_path))
    record = store.update(
        job_id,
        step=f"queued whisper={job_settings.whisper_model_size} translation={job_settings.translation_model}",
    )
    background_tasks.add_task(run_job, job_id, saved_path, store, job_settings)
    return record.to_dict()


@app.post("/jobs/batch")
async def create_batch_jobs(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    whisper_model_size: str = Form(default=settings.whisper_model_size),
    translation_model: str = Form(default=settings.translation_model),
) -> dict[str, object]:
    jobs = []
    job_settings = _settings_for_job(whisper_model_size, translation_model)
    for file in files:
        job_id, saved_path = await _save_upload(file)
        record = store.create(job_id, str(saved_path))
        store.update(
            job_id,
            step=f"queued whisper={job_settings.whisper_model_size} translation={job_settings.translation_model}",
        )
        background_tasks.add_task(run_job, job_id, saved_path, store, job_settings)
        jobs.append(record.to_dict())
    return {"jobs": jobs}


@app.get("/jobs")
def list_jobs(limit: int = 50) -> dict[str, object]:
    return {"jobs": [record.to_dict() for record in store.list_recent(limit=limit)]}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return record.to_dict()


@app.get("/jobs/{job_id}/logs")
def get_job_logs(job_id: str) -> dict[str, object]:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "logs": record.logs}


@app.get("/jobs/{job_id}/subtitle")
def download_subtitle(job_id: str) -> FileResponse:
    record = _completed_job(job_id)
    if not record.subtitle_path:
        raise HTTPException(status_code=404, detail="Subtitle not available")
    return _file_response(record.subtitle_path, "text/plain")


@app.get("/jobs/{job_id}/video")
def download_video(job_id: str) -> FileResponse:
    record = _completed_job(job_id)
    if not record.video_path:
        raise HTTPException(status_code=404, detail="Rendered video not available")
    return _file_response(record.video_path, "video/mp4")


async def _save_upload(file: UploadFile) -> tuple[str, Path]:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_video_extensions:
        raise HTTPException(status_code=400, detail="Only .mp4 and .mkv files are supported")

    job_id = new_job_id()
    safe_name = Path(file.filename or f"video{suffix}").name
    destination = settings.upload_dir / job_id / safe_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return job_id, destination


def _completed_job(job_id: str):
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if record.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job is {record.status}, not completed")
    return record


def _file_response(path_value: str, media_type: str) -> FileResponse:
    path = Path(path_value)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output file missing on disk")
    return FileResponse(path, media_type=media_type, filename=path.name)


def _settings_for_job(whisper_model_size: str, translation_model: str) -> Settings:
    if whisper_model_size not in WHISPER_MODEL_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported Whisper model. Choose one of: {', '.join(WHISPER_MODEL_OPTIONS)}",
        )
    if translation_model not in TRANSLATION_MODEL_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported translation model. Choose one of: {', '.join(TRANSLATION_MODEL_OPTIONS)}",
        )
    return replace(
        settings,
        whisper_model_size=whisper_model_size,
        translation_model=translation_model,
    )
