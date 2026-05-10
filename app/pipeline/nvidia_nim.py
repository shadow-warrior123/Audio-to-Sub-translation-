from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import Settings
from app.pipeline.models import Segment
from app.pipeline.transcribe import _wav_duration

logger = logging.getLogger(__name__)


class NvidiaNimError(RuntimeError):
    pass


def transcribe_with_nvidia_nim(audio_path: Path, settings: Settings, task: str) -> list[Segment]:
    if not settings.nvidia_api_key:
        raise NvidiaNimError("NVIDIA_API_KEY is not configured.")
    if task not in {"transcribe", "translate"}:
        raise NvidiaNimError(f"Unsupported NVIDIA NIM Whisper task: {task}")

    try:
        import riva.client
    except ImportError as exc:
        raise NvidiaNimError("nvidia-riva-client is required for NVIDIA NIM Whisper.") from exc

    metadata = [
        ["function-id", settings.nvidia_nim_function_id],
        ["authorization", f"Bearer {settings.nvidia_api_key}"],
    ]
    auth = riva.client.Auth(
        uri=settings.nvidia_nim_server,
        use_ssl=True,
        metadata_args=metadata,
    )
    service = riva.client.ASRService(auth)
    config = riva.client.RecognitionConfig()
    config.language_code = settings.nvidia_nim_language_code
    config.max_alternatives = 1
    config.enable_automatic_punctuation = True
    config.enable_word_time_offsets = True
    config.audio_channel_count = 1
    if task == "translate":
        config.custom_configuration["task"] = "translate"

    logger.info("Calling NVIDIA NIM Whisper Large v3 task=%s language=%s", task, config.language_code)
    try:
        audio_bytes = audio_path.read_bytes()
        response = service.offline_recognize(audio_bytes, config)
    except Exception as exc:
        raise NvidiaNimError(f"NVIDIA NIM Whisper request failed: {exc}") from exc

    return _segments_from_riva_response(response, audio_path)


def _segments_from_riva_response(response, audio_path: Path) -> list[Segment]:
    segments: list[Segment] = []
    transcript_parts: list[str] = []
    for result in response.results:
        if not result.alternatives:
            continue
        alternative = result.alternatives[0]
        transcript = alternative.transcript.strip()
        if transcript:
            transcript_parts.append(transcript)
        words = list(alternative.words)
        if words:
            segments.extend(_group_words(words))

    if segments:
        return segments

    transcript = " ".join(transcript_parts).strip()
    if not transcript:
        raise NvidiaNimError("NVIDIA NIM Whisper returned no transcript.")
    duration = max(_wav_duration(audio_path), 0.2)
    return [Segment(0.0, duration, transcript)]


def _group_words(words) -> list[Segment]:
    grouped: list[Segment] = []
    current_words: list[str] = []
    current_start: float | None = None
    current_end = 0.0

    for word_info in words:
        word = word_info.word.strip()
        if not word:
            continue
        start = _duration_to_seconds(word_info.start_time)
        end = _duration_to_seconds(word_info.end_time)
        if current_start is None:
            current_start = start
        current_words.append(word)
        current_end = max(end, start + 0.2)

        text = " ".join(current_words)
        should_close = (
            text.endswith((".", "?", "!", "。", "？", "！"))
            or (current_start is not None and current_end - current_start >= 5.0)
            or len(text) >= 80
        )
        if should_close and current_start is not None:
            grouped.append(Segment(current_start, current_end, text))
            current_words = []
            current_start = None

    if current_words and current_start is not None:
        grouped.append(Segment(current_start, current_end, " ".join(current_words)))
    return grouped


def _duration_to_seconds(duration) -> float:
    return float(getattr(duration, "seconds", 0)) + float(getattr(duration, "nanos", 0)) / 1_000_000_000.0
