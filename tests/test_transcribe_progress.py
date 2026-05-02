from pathlib import Path

from app.pipeline.transcribe import _format_seconds, _wav_duration


def test_format_seconds():
    assert _format_seconds(65) == "01:05"
    assert _format_seconds(3661) == "01:01:01"


def test_wav_duration_returns_zero_for_missing_file():
    assert _wav_duration(Path("missing.wav")) == 0.0
