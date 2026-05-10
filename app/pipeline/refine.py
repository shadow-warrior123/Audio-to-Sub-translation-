from __future__ import annotations

import re

from app.pipeline.models import Segment

BOUNDARY_RE = re.compile(r"(?<=[。！？!?])")
NOISY_RE = re.compile(r"^[\s♪♫。、…・\-ー]+$")


def clean_segments(segments: list[Segment]) -> list[Segment]:
    cleaned: list[Segment] = []
    for segment in segments:
        text = re.sub(r"\s+", " ", segment.text).strip()
        if not text or NOISY_RE.fullmatch(text):
            continue
        if segment.end <= segment.start:
            continue
        cleaned.append(Segment(segment.start, segment.end, text))
    return cleaned


def merge_short_segments(segments: list[Segment], min_duration: float = 1.0) -> list[Segment]:
    merged: list[Segment] = []
    i = 0
    while i < len(segments):
        current = segments[i]
        if current.duration >= min_duration or len(segments) == 1:
            merged.append(current)
            i += 1
            continue

        if i + 1 < len(segments):
            nxt = segments[i + 1]
            merged.append(Segment(current.start, nxt.end, f"{current.text} {nxt.text}".strip()))
            i += 2
        elif merged:
            prev = merged.pop()
            merged.append(Segment(prev.start, current.end, f"{prev.text} {current.text}".strip()))
            i += 1
        else:
            merged.append(current)
            i += 1
    return merged


def _split_text(text: str, parts: int) -> list[str]:
    chunks = [chunk.strip() for chunk in BOUNDARY_RE.split(text) if chunk.strip()]
    if len(chunks) >= parts:
        return _rebalance_chunks(chunks, parts)

    words = text.split()
    if len(words) >= parts:
        size = max(1, round(len(words) / parts))
        return [" ".join(words[i : i + size]).strip() for i in range(0, len(words), size)]

    char_size = max(1, round(len(text) / parts))
    return [text[i : i + char_size].strip() for i in range(0, len(text), char_size) if text[i : i + char_size].strip()]


def _rebalance_chunks(chunks: list[str], parts: int) -> list[str]:
    if len(chunks) == parts:
        return chunks
    target_chars = max(1, sum(len(chunk) for chunk in chunks) // parts)
    balanced: list[str] = []
    current = ""
    for chunk in chunks:
        candidate = f"{current}{chunk}" if current else chunk
        if current and len(candidate) > target_chars and len(balanced) < parts - 1:
            balanced.append(current)
            current = chunk
        else:
            current = candidate
    if current:
        balanced.append(current)
    while len(balanced) > parts:
        tail = balanced.pop()
        balanced[-1] = f"{balanced[-1]}{tail}"
    return balanced


def split_long_segments(segments: list[Segment], max_duration: float = 5.0) -> list[Segment]:
    result: list[Segment] = []
    for segment in segments:
        if segment.duration <= max_duration:
            result.append(segment)
            continue

        parts = max(2, int(segment.duration // max_duration) + (1 if segment.duration % max_duration else 0))
        text_parts = _split_text(segment.text, parts)
        part_duration = segment.duration / len(text_parts)
        for index, text in enumerate(text_parts):
            start = segment.start + index * part_duration
            end = segment.start + (index + 1) * part_duration
            result.append(Segment(start, end, text))
    return result


def refine_segments(
    segments: list[Segment],
    min_duration: float = 1.0,
    max_duration: float = 5.0,
) -> list[Segment]:
    cleaned = clean_segments(segments)
    merged = merge_short_segments(cleaned, min_duration=min_duration)
    return split_long_segments(merged, max_duration=max_duration)

