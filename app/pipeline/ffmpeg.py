from __future__ import annotations

import shutil

from app.core.config import Settings


def resolve_ffmpeg_path(settings: Settings) -> str | None:
    system_path = shutil.which(settings.ffmpeg_path)
    if system_path:
        return system_path

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def ffmpeg_available(settings: Settings) -> bool:
    return resolve_ffmpeg_path(settings) is not None

