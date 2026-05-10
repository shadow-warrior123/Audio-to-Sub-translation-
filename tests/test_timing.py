from app.pipeline.models import Segment
from app.pipeline.timing import optimize_subtitle_timing


def test_timing_adds_padding_and_prevents_overlap():
    segments = [
        Segment(1.0, 2.0, "Hello world"),
        Segment(2.1, 3.0, "Next line"),
    ]

    result = optimize_subtitle_timing(segments, start_padding=0.1, end_padding=0.2)

    assert result[0].start == 0.9
    assert result[0].end < result[1].start


def test_timing_enforces_reading_speed_when_possible():
    segments = [Segment(1.0, 1.2, "a" * 30)]

    result = optimize_subtitle_timing(segments, start_padding=0, end_padding=0, chars_per_second=15)

    assert result[0].duration >= 2.0

