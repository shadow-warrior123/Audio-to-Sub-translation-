from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Callable

from app.core.config import Settings
from app.pipeline.audio import extract_audio
from app.pipeline.models import PipelineOutputs
from app.pipeline.refine import refine_segments
from app.pipeline.render import burn_subtitles
from app.pipeline.srt import write_srt
from app.pipeline.timing import optimize_subtitle_timing
from app.pipeline.transcribe import transcribe_japanese
from app.pipeline.translate import HuggingFaceTranslator, Translator, translate_segments

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[int, str], None]


class PipelineError(RuntimeError):
    pass


def process_video(
    video_path: Path,
    output_dir: Path,
    settings: Settings,
    job_id: str | None = None,
    progress: ProgressCallback | None = None,
    translator: Translator | None = None,
) -> PipelineOutputs:
    job_id = job_id or uuid.uuid4().hex
    job_output_dir = output_dir / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)

    def report(percent: int, step: str) -> None:
        logger.info("[%s] %s (%s%%)", job_id, step, percent)
        if progress:
            progress(percent, step)

    source_stem = video_path.stem
    audio_path = job_output_dir / f"{source_stem}.16k.wav"
    subtitle_path = job_output_dir / f"{source_stem}.en.srt"
    rendered_path = job_output_dir / f"{source_stem}.hardsub.mp4"

    try:
        report(5, "extracting_audio")
        extract_audio(video_path, audio_path, settings)

        report(20, "transcribing_japanese")
        segments = transcribe_japanese(
            audio_path,
            settings,
            progress=progress,
            progress_start=20,
            progress_end=45,
        )

        report(45, "refining_segments")
        refined = refine_segments(
            segments,
            min_duration=settings.min_merge_duration,
            max_duration=settings.max_segment_duration,
        )

        report(55, "translating_to_english")
        active_translator = translator or HuggingFaceTranslator(settings)
        translated = translate_segments(refined, active_translator)

        report(70, "optimizing_subtitle_timing")
        timed = optimize_subtitle_timing(
            translated,
            start_padding=settings.subtitle_start_padding,
            end_padding=settings.subtitle_end_padding,
            chars_per_second=settings.subtitle_chars_per_second,
        )

        report(80, "writing_srt")
        write_srt(
            subtitle_path,
            timed,
            max_chars=settings.subtitle_max_line_chars,
            max_lines=settings.subtitle_max_lines,
        )

        report(90, "rendering_video")
        burn_subtitles(video_path, subtitle_path, rendered_path, settings)

        report(100, "completed")
        return PipelineOutputs(
            job_id=job_id,
            source_video=str(video_path),
            audio_path=str(audio_path),
            subtitle_path=str(subtitle_path),
            rendered_video_path=str(rendered_path),
            segment_count=len(timed),
        )
    except Exception as exc:
        raise PipelineError(f"Pipeline failed for {video_path}: {exc}") from exc
