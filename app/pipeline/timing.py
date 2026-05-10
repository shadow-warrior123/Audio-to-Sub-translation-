from __future__ import annotations

from app.pipeline.models import Segment


def optimize_subtitle_timing(
    segments: list[Segment],
    start_padding: float = 0.1,
    end_padding: float = 0.2,
    chars_per_second: float = 15.0,
    min_gap: float = 0.03,
) -> list[Segment]:
    if not segments:
        return []

    optimized: list[Segment] = []
    for segment in segments:
        start = max(0.0, segment.start - start_padding)
        min_duration = len(segment.text) / chars_per_second if chars_per_second > 0 else segment.duration
        end = max(segment.end + end_padding, start + min_duration)
        optimized.append(Segment(start, end, segment.text))

    final: list[Segment] = []
    for index, segment in enumerate(optimized):
        if index + 1 < len(optimized):
            next_start = optimized[index + 1].start
            end = min(segment.end, max(segment.start + 0.2, next_start - min_gap))
        else:
            end = segment.end
        final.append(Segment(segment.start, max(segment.start + 0.2, end), segment.text))
    return final

