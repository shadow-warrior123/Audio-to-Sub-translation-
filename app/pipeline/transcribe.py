from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable
import wave

from app.core.config import Settings
from app.pipeline.models import Segment

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[int, str], None]


class TranscriptionError(RuntimeError):
    pass


def _cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def resolve_whisper_runtime(settings: Settings) -> tuple[str, str]:
    if settings.whisper_device != "auto":
        device = settings.whisper_device
    else:
        device = "cuda" if _cuda_available() else "cpu"

    if settings.whisper_compute_type != "auto":
        compute_type = settings.whisper_compute_type
    else:
        compute_type = "float16" if device == "cuda" else "int8"

    return device, compute_type


def transcribe_japanese(
    audio_path: Path,
    settings: Settings,
    progress: ProgressCallback | None = None,
    progress_start: int = 20,
    progress_end: int = 45,
) -> list[Segment]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionError(
            "faster-whisper is not installed. Install requirements.txt first."
        ) from exc

    device, compute_type = resolve_whisper_runtime(settings)
    logger.info(
        "Loading faster-whisper model=%s device=%s compute_type=%s",
        settings.whisper_model_size,
        device,
        compute_type,
    )
    try:
        model = WhisperModel(
            settings.whisper_model_size,
            device=device,
            compute_type=compute_type,
        )
        audio_duration = _wav_duration(audio_path)
        raw_segments, info = model.transcribe(
            str(audio_path),
            language="ja",
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=False,
        )
        logger.info("Transcription language=%s probability=%.3f", info.language, info.language_probability)
        segments: list[Segment] = []
        last_percent = progress_start
        for item in raw_segments:
            segment = Segment(start=float(item.start), end=float(item.end), text=item.text.strip())
            segments.append(segment)
            if progress and audio_duration > 0:
                ratio = min(1.0, max(0.0, segment.end / audio_duration))
                percent = progress_start + int((progress_end - progress_start) * ratio)
                if percent > last_percent:
                    last_percent = percent
                    progress(percent, f"transcribing_japanese {_format_seconds(segment.end)} / {_format_seconds(audio_duration)}")
    except Exception as exc:
        raise TranscriptionError(f"Japanese transcription failed: {exc}") from exc

    if not segments:
        raise TranscriptionError("No speech segments were detected.")
    return segments


def _wav_duration(audio_path: Path) -> float:
    try:
        with wave.open(str(audio_path), "rb") as wav_file:
            frame_count = wav_file.getnframes()
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return 0.0
            return frame_count / float(frame_rate)
    except Exception:
        logger.warning("Could not read WAV duration for progress tracking: %s", audio_path)
        return 0.0


def _format_seconds(seconds: float) -> str:
    total = int(max(0.0, seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"
