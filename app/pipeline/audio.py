from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.core.config import Settings
from app.pipeline.ffmpeg import ffmpeg_available, resolve_ffmpeg_path

logger = logging.getLogger(__name__)


class AudioExtractionError(RuntimeError):
    pass


def extract_audio(video_path: Path, audio_path: Path, settings: Settings) -> Path:
    ffmpeg_path = resolve_ffmpeg_path(settings)
    if ffmpeg_path is None:
        raise AudioExtractionError("FFmpeg is not installed and imageio-ffmpeg is unavailable.")

    audio_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-acodec",
        "pcm_s16le",
        str(audio_path),
    ]
    logger.info("Extracting mono 16 kHz WAV audio: %s", audio_path)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise AudioExtractionError(
            "FFmpeg failed to extract audio. "
            f"stderr={result.stderr[-2000:] if result.stderr else '<empty>'}"
        )
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise AudioExtractionError("FFmpeg produced an empty audio file.")
    return audio_path
