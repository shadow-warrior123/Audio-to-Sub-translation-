from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from app.core.config import Settings
from app.pipeline.ffmpeg import resolve_ffmpeg_path

logger = logging.getLogger(__name__)


class RenderError(RuntimeError):
    pass


def burn_subtitles(video_path: Path, subtitle_path: Path, output_path: Path, settings: Settings) -> Path:
    ffmpeg_path = resolve_ffmpeg_path(settings)
    if ffmpeg_path is None:
        raise RenderError("FFmpeg is not installed and imageio-ffmpeg is unavailable.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subtitle_filter = _subtitle_filter_path(subtitle_path)
    force_style = (
        "FontName=Arial,"
        "FontSize=24,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=36"
    )
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"subtitles='{subtitle_filter}':force_style='{force_style}'",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        str(output_path),
    ]
    logger.info("Burning subtitles into video: %s", output_path)
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(
            "FFmpeg failed to render hardcoded subtitles. "
            f"stderr={result.stderr[-2000:] if result.stderr else '<empty>'}"
        )
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RenderError("FFmpeg produced an empty rendered video.")
    return output_path


def _subtitle_filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    return value
