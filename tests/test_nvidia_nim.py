from app.pipeline.nvidia_nim import _duration_to_seconds


class Duration:
    seconds = 2
    nanos = 500_000_000


def test_duration_to_seconds():
    assert _duration_to_seconds(Duration()) == 2.5
