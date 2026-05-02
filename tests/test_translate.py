from app.pipeline.models import Segment
from app.pipeline.translate import Translator, translate_segments


class MockTranslator(Translator):
    def translate_batch(self, texts: list[str]) -> list[str]:
        return [f"en:{text}" for text in texts]


def test_translate_segments_preserves_timing():
    segments = [Segment(1, 2, "こんにちは")]

    translated = translate_segments(segments, MockTranslator())

    assert translated == [Segment(1, 2, "en:こんにちは")]

