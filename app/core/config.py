from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

WHISPER_MODEL_OPTIONS: tuple[str, ...] = (
    "tiny",
    "base",
    "small",
    "medium",
    "large-v1",
    "large-v2",
    "large-v3",
)

TRANSLATION_MODEL_OPTIONS: tuple[str, ...] = (
    "Helsinki-NLP/opus-mt-ja-en",
    "staka/fugumt-ja-en",
    "facebook/nllb-200-distilled-600M",
    "Mitsua/elan-mt-bt-ja-en",
)

SPEECH_BACKEND_OPTIONS: tuple[str, ...] = (
    "local_faster_whisper",
    "nvidia_nim_whisper_large_v3_transcribe",
    "nvidia_nim_whisper_large_v3_translate",
)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Anime Subtitle Backend"
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "data/uploads"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "data/outputs"))
    database_path: Path = Path(os.getenv("DATABASE_PATH", "data/jobs.sqlite3"))

    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    speech_backend: str = os.getenv("SPEECH_BACKEND", "local_faster_whisper")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "auto")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "auto")

    nvidia_api_key: str | None = os.getenv("NVIDIA_API_KEY")
    nvidia_nim_server: str = os.getenv("NVIDIA_NIM_SERVER", "grpc.nvcf.nvidia.com:443")
    nvidia_nim_function_id: str = os.getenv(
        "NVIDIA_NIM_FUNCTION_ID",
        "b702f636-f60c-4a3d-a6f4-f3568c13bd7d",
    )
    nvidia_nim_language_code: str = os.getenv("NVIDIA_NIM_LANGUAGE_CODE", "ja")

    translation_model: str = os.getenv("TRANSLATION_MODEL", "Helsinki-NLP/opus-mt-ja-en")
    translation_device: str = os.getenv("TRANSLATION_DEVICE", "cpu")
    translation_batch_size: int = int(os.getenv("TRANSLATION_BATCH_SIZE", "8"))
    translation_max_new_tokens: int = int(os.getenv("TRANSLATION_MAX_NEW_TOKENS", "96"))

    min_merge_duration: float = float(os.getenv("MIN_MERGE_DURATION", "1.0"))
    max_segment_duration: float = float(os.getenv("MAX_SEGMENT_DURATION", "5.0"))
    subtitle_start_padding: float = float(os.getenv("SUBTITLE_START_PADDING", "0.1"))
    subtitle_end_padding: float = float(os.getenv("SUBTITLE_END_PADDING", "0.2"))
    subtitle_chars_per_second: float = float(os.getenv("SUBTITLE_CHARS_PER_SECOND", "15"))
    subtitle_max_line_chars: int = int(os.getenv("SUBTITLE_MAX_LINE_CHARS", "40"))
    subtitle_max_lines: int = int(os.getenv("SUBTITLE_MAX_LINES", "2"))

    ffmpeg_path: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    ffprobe_path: str = os.getenv("FFPROBE_PATH", "ffprobe")
    keep_intermediate_audio: bool = _bool_env("KEEP_INTERMEDIATE_AUDIO", True)

    allowed_video_extensions: tuple[str, ...] = (".mp4", ".mkv")

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
