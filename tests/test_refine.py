from app.pipeline.models import Segment
from app.pipeline.refine import clean_segments, merge_short_segments, split_long_segments


def test_clean_segments_removes_empty_and_noise():
    segments = [
        Segment(0, 1, ""),
        Segment(1, 2, "♪"),
        Segment(2, 3, "こんにちは"),
    ]

    assert clean_segments(segments) == [Segment(2, 3, "こんにちは")]


def test_merge_short_segments_with_next_segment():
    segments = [
        Segment(0, 0.5, "やあ"),
        Segment(0.5, 2.0, "元気？"),
    ]

    assert merge_short_segments(segments, min_duration=1.0) == [
        Segment(0, 2.0, "やあ 元気？")
    ]


def test_split_long_segments_prefers_sentence_boundaries():
    segments = [Segment(0, 10, "これは長い文です。次の文です。最後です。")]

    result = split_long_segments(segments, max_duration=5.0)

    assert len(result) == 2
    assert result[0].start == 0
    assert result[-1].end == 10

