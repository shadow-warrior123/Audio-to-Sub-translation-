from __future__ import annotations

import textwrap
from pathlib import Path

from app.pipeline.models import Segment


def format_timestamp(seconds: float) -> str:
    milliseconds = round(max(0.0, seconds) * 1000)
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    secs = milliseconds // 1000
    milliseconds %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def wrap_subtitle_text(text: str, max_chars: int = 40, max_lines: int = 2) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return ""

    lines = textwrap.wrap(
        normalized,
        width=max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if len(lines) <= max_lines:
        return "\n".join(lines)

    kept = lines[: max_lines - 1]
    remaining = " ".join(lines[max_lines - 1 :])
    kept.append(_truncate_to_width(remaining, max_chars))
    return "\n".join(kept)


def _truncate_to_width(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    suffix = "..."
    return text[: max(0, max_chars - len(suffix))].rstrip() + suffix


def build_srt(segments: list[Segment], max_chars: int = 40, max_lines: int = 2) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        text = wrap_subtitle_text(segment.text, max_chars=max_chars, max_lines=max_lines)
        blocks.append(
            f"{index}\n"
            f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}\n"
            f"{text}"
        )
    return "\n\n".join(blocks) + "\n"


def write_srt(path: Path, segments: list[Segment], max_chars: int = 40, max_lines: int = 2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_srt(segments, max_chars=max_chars, max_lines=max_lines), encoding="utf-8")
    return path
