from __future__ import annotations

import logging
import time
from typing import Any, Callable

from editor.editor_models import (
    TranslationRequest, TranslationResponse, utc_now,
)

logger = logging.getLogger(__name__)

LANGUAGE_MAP: dict[str, str] = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
    "nl": "Dutch", "tr": "Turkish", "vi": "Vietnamese", "th": "Thai",
    "pl": "Polish", "sv": "Swedish", "da": "Danish", "fi": "Finnish",
    "no": "Norwegian", "cs": "Czech", "ro": "Romanian", "hu": "Hungarian",
    "el": "Greek", "he": "Hebrew", "id": "Indonesian", "ms": "Malay",
    "bn": "Bengali", "ta": "Tamil", "te": "Telugu", "mr": "Marathi",
    "ur": "Urdu", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "pa": "Punjabi", "uk": "Ukrainian", "bg": "Bulgarian", "sr": "Serbian",
    "hr": "Croatian", "sk": "Slovak", "sl": "Slovenian", "lt": "Lithuanian",
    "lv": "Latvian", "et": "Estonian", "ka": "Georgian", "hy": "Armenian",
    "az": "Azerbaijani", "fa": "Persian", "sw": "Swahili", "tl": "Filipino",
    "af": "Afrikaans", "cy": "Welsh", "ga": "Irish", "mt": "Maltese",
    "is": "Icelandic", "lb": "Luxembourgish", "sq": "Albanian", "mk": "Macedonian",
    "mn": "Mongolian", "ne": "Nepalese", "si": "Sinhala", "am": "Amharic",
    "zu": "Zulu", "xh": "Xhosa", "jw": "Javanese", "su": "Sundanese",
    "my": "Burmese", "km": "Khmer", "lo": "Lao", "gl": "Galician",
    "eu": "Basque", "ca": "Catalan", "oc": "Occitan", "fy": "Frisian",
    "gd": "Scottish Gaelic", "co": "Corsican", "ht": "Haitian Creole",
    "mg": "Malagasy", "ny": "Chichewa", "ha": "Hausa", "ig": "Igbo",
    "yo": "Yoruba", "so": "Somali", "st": "Sesotho", "tn": "Tswana",
    "rw": "Kinyarwanda", "sn": "Shona", "sm": "Samoan", "to": "Tongan",
}


class TranslationEngine:
    def __init__(self):
        self._llm_provider: Any = None
        self._change_listeners: list[Callable] = []

    def set_llm_provider(self, provider: Any) -> None:
        self._llm_provider = provider

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        start_time = time.time()
        self._emit("translation_started", {
            "target_language": request.target_language,
            "scope": request.scope,
        })

        try:
            if self._llm_provider:
                result = self._translate_with_llm(request)
            else:
                result = self._translate_local(request)

            elapsed = (time.time() - start_time) * 1000
            result.processing_time_ms = round(elapsed, 2)
            self._emit("translation_completed", {
                "target_language": request.target_language,
                "success": result.success,
                "processing_time_ms": result.processing_time_ms,
            })
            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"Translation failed: {e}")
            return TranslationResponse(
                success=False,
                original_text=request.text,
                source_language=request.source_language,
                target_language=request.target_language,
                error=str(e),
                processing_time_ms=round(elapsed, 2),
            )

    def _translate_with_llm(self, request: TranslationRequest) -> TranslationResponse:
        prompt = self._build_translation_prompt(request)
        try:
            result = self._llm_provider.generate(prompt, temperature=0.3, max_tokens=4096)
            return TranslationResponse(
                success=True,
                original_text=request.text,
                translated_text=result.text.strip(),
                source_language=request.source_language,
                target_language=request.target_language,
                detection_confidence=1.0,
            )
        except Exception as e:
            raise

    def _translate_local(self, request: TranslationRequest) -> TranslationResponse:
        return TranslationResponse(
            success=True,
            original_text=request.text,
            translated_text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            detection_confidence=0.0,
            error="LLM provider not configured; returning original text",
        )

    def _build_translation_prompt(self, request: TranslationRequest) -> str:
        source_name = LANGUAGE_MAP.get(request.source_language, request.source_language)
        target_name = LANGUAGE_MAP.get(request.target_language, request.target_language)

        preserve = ""
        if request.preserve_formatting:
            preserve = (
                "\nIMPORTANT: Preserve all Markdown formatting, including:\n"
                "- Headings (#, ##, etc.)\n"
                "- Bold (**), italic (*), strikethrough (~~)\n"
                "- Code blocks (```) and inline code (`)\n"
                "- Links [text](url) — do NOT translate URLs\n"
                "- Images ![alt](url) — do NOT translate URLs\n"
                "- Tables, blockquotes, lists\n"
                "- Any HTML tags\n"
                "- Horizontal rules (---)"
            )

        return (
            f"Translate the following text from {source_name} to {target_name}.{preserve}\n\n"
            f"Source ({request.source_language}):\n{request.text}\n\n"
            f"Translation ({request.target_language}):"
        )

    def get_supported_languages(self) -> list[dict[str, str]]:
        return [
            {"code": code, "name": name}
            for code, name in sorted(LANGUAGE_MAP.items(), key=lambda x: x[1])
        ]

    def detect_language(self, text: str) -> tuple[str, float]:
        if len(text) < 20:
            return ("en", 0.0)
        try:
            import langdetect
            lang = langdetect.detect(text)
            confidence = 0.8
            return (lang, confidence)
        except ImportError:
            pass
        except Exception:
            pass

        latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total_chars = sum(1 for c in text if c.isalpha())
        if total_chars > 0 and latin_chars / total_chars > 0.9:
            common_en_words = ["the", "and", "is", "in", "to", "of", "a", "for", "on", "with", "that", "this", "as", "are", "be", "has", "was", "by", "an", "it", "or", "from", "at", "but", "not", "we", "you", "they", "have", "do", "will", "can", "would", "could", "should"]
            words = text.lower().split()
            en_score = sum(1 for w in words if w.strip(".,!?;:'\"()[]") in common_en_words)
            if len(words) > 0 and en_score / len(words) > 0.15:
                return ("en", 0.7)
            return ("es", 0.4)
        cjk_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff")
        if cjk_chars > 5:
            return ("ja", 0.6) if "\u3040" <= text[0] <= "\u30ff" else ("zh", 0.6)
        cyrillic_chars = sum(1 for c in text if "\u0400" <= c <= "\u04ff")
        if cyrillic_chars > 5:
            return ("ru", 0.6)
        devanagari_chars = sum(1 for c in text if "\u0900" <= c <= "\u097f")
        if devanagari_chars > 5:
            return ("hi", 0.6)
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        if arabic_chars > 5:
            return ("ar", 0.6)
        return ("en", 0.0)

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Translation listener error: {e}")
