from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def with_text(self, text: str) -> "Segment":
        return replace(self, text=text)


@dataclass(frozen=True)
class PipelineOutputs:
    job_id: str
    source_video: str
    audio_path: str
    subtitle_path: str
    rendered_video_path: str
    segment_count: int

