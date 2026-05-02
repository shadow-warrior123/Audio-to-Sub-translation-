from app.pipeline.models import Segment
from app.pipeline.srt import build_srt, format_timestamp, wrap_subtitle_text


def test_format_timestamp():
    assert format_timestamp(3723.456) == "01:02:03,456"


def test_wrap_subtitle_text_limits_lines():
    text = "This is a fairly long subtitle line that should wrap neatly into only two lines."

    wrapped = wrap_subtitle_text(text, max_chars=20, max_lines=2)

    lines = wrapped.splitlines()
    assert len(lines) == 2
    assert all(len(line) <= 20 for line in lines)


def test_build_srt():
    srt = build_srt([Segment(0, 1.25, "Hello there.")])

    assert "1\n00:00:00,000 --> 00:00:01,250\nHello there.\n" == srt

