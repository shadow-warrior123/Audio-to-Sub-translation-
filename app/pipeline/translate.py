from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Iterable

from app.core.config import Settings
from app.pipeline.models import Segment

logger = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    pass


class Translator(ABC):
    @abstractmethod
    def translate_batch(self, texts: list[str]) -> list[str]:
        raise NotImplementedError


class HuggingFaceTranslator(Translator):
    def __init__(self, settings: Settings):
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise TranslationError(
                "transformers and torch are required for local Hugging Face translation."
            ) from exc

        self.settings = settings
        self.model_id = settings.translation_model
        self.batch_size = settings.translation_batch_size
        self.max_new_tokens = settings.translation_max_new_tokens
        self.torch = torch
        logger.info("Loading translation model=%s device=%s", self.model_id, settings.translation_device)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id)

        self.device = self._resolve_device(settings.translation_device)
        self.model.to(self.device)
        self.model.eval()

    def _resolve_device(self, configured: str) -> str:
        if configured == "auto":
            return "cuda" if self.torch.cuda.is_available() else "cpu"
        if configured == "cuda" and not self.torch.cuda.is_available():
            logger.warning("CUDA requested for translation but unavailable; falling back to CPU.")
            return "cpu"
        return configured

    def translate_batch(self, texts: list[str]) -> list[str]:
        if not texts:
            return []

        outputs: list[str] = []
        for batch in _chunks(texts, self.batch_size):
            try:
                self._prepare_source_language()
                inputs = self.tokenizer(
                    batch,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=256,
                ).to(self.device)
                generate_kwargs = {
                    "max_new_tokens": self.max_new_tokens,
                    "num_beams": 4,
                    "early_stopping": True,
                }
                forced_bos_token_id = self._forced_bos_token_id()
                if forced_bos_token_id is not None:
                    generate_kwargs["forced_bos_token_id"] = forced_bos_token_id
                with self.torch.no_grad():
                    generated = self.model.generate(**inputs, **generate_kwargs)
                outputs.extend(
                    text.strip()
                    for text in self.tokenizer.batch_decode(generated, skip_special_tokens=True)
                )
            except Exception as exc:
                raise TranslationError(f"Translation failed: {exc}") from exc
        return outputs

    def _prepare_source_language(self) -> None:
        if "nllb" in self.model_id.lower():
            self.tokenizer.src_lang = "jpn_Jpan"

    def _forced_bos_token_id(self) -> int | None:
        if "nllb" not in self.model_id.lower():
            return None
        token_id = getattr(self.tokenizer, "lang_code_to_id", {}).get("eng_Latn")
        return token_id


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    size = max(1, size)
    for index in range(0, len(items), size):
        yield items[index : index + size]


def translate_segments(segments: list[Segment], translator: Translator) -> list[Segment]:
    translated = translator.translate_batch([segment.text for segment in segments])
    if len(translated) != len(segments):
        raise TranslationError("Translator returned a different number of segments.")
    return [segment.with_text(text) for segment, text in zip(segments, translated, strict=True)]
