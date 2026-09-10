"""Enhanced Language Detection — 4-level detection pipeline.

Level 1: YouTube transcript metadata (highest confidence)
Level 2: langdetect library
Level 3: Character-range heuristics (CJK/Cyrillic/Latin/Devanagari/Arabic)
Level 4: Keyword-based fallback

Returns primary, secondary, mixed language detection with confidence.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from transcript_reliability.models import LanguageDetectionResult

logger = logging.getLogger(__name__)

# Try optional langdetect library
try:
    from langdetect import detect as langdetect_detect, detect_langs as langdetect_detect_langs, DetectorFactory, LangDetectException
    DetectorFactory.seed = 42
    _HAS_LANGDETECT = True
except ImportError:
    _HAS_LANGDETECT = False

# ISO 639-1 language codes mapped to common names
_LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
    "bn": "Bengali", "pa": "Punjabi", "ta": "Tamil", "te": "Telugu",
    "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "nl": "Dutch", "pl": "Polish", "tr": "Turkish", "vi": "Vietnamese",
    "th": "Thai", "sv": "Swedish", "da": "Danish", "fi": "Finnish",
    "no": "Norwegian", "cs": "Czech", "hu": "Hungarian", "ro": "Romanian",
    "el": "Greek", "he": "Hebrew", "id": "Indonesian", "ms": "Malay",
}

# Character range patterns for heuristic detection
_UNICODE_PATTERNS: dict[str, tuple[str, float]] = {
    "zh": (r"[\u4e00-\u9fff\u3400-\u4dbf]", 0.1),
    "ja": (r"[\u3040-\u309f\u30a0-\u30ff]", 0.05),
    "ko": (r"[\uac00-\ud7af\u1100-\u11ff]", 0.1),
    "ru": (r"[\u0400-\u04ff]", 0.1),
    "ar": (r"[\u0600-\u06ff]", 0.1),
    "hi": (r"[\u0900-\u097f]", 0.1),
    "th": (r"[\u0e00-\u0e7f]", 0.1),
    "el": (r"[\u0370-\u03ff]", 0.1),
    "he": (r"[\u0590-\u05ff]", 0.1),
}

# Common words per language for keyword-based detection
_LANGUAGE_KEYWORDS: dict[str, list[str]] = {
    "en": ["the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was", "one", "our", "out"],
    "es": ["que", "los", "las", "del", "por", "con", "una", "para", "como", "más", "pero", "sus"],
    "fr": ["que", "pas", "une", "sur", "dans", "avec", "pour", "tout", "plus", "mais", "être", "avoir"],
    "de": ["die", "der", "und", "das", "sich", "nicht", "auch", "sein", "oder", "aber", "noch", "wird"],
    "hi": ["में", "है", "का", "की", "से", "को", "एक", "हैं", "यह", "पर", "के", "वह"],
}


class LanguageDetector:
    """4-level language detection for transcript text.

    Uses metadata first, then library detection, then heuristics,
    then keyword analysis — in order of decreasing confidence.
    """

    def detect(
        self,
        text: str,
        metadata_language: str | None = None,
        metadata_confidence: float | None = None,
    ) -> LanguageDetectionResult:
        """Detect language using the 4-level pipeline.

        Args:
            text: Transcript text to analyze (minimum ~50 chars recommended).
            metadata_language: Language code from provider metadata (Level 1).
            metadata_confidence: Confidence from provider metadata (0.0-1.0).

        Returns:
            ``LanguageDetectionResult`` with primary, secondary, confidence.
        """
        if not text or len(text.strip()) < 10:
            return LanguageDetectionResult(
                primary=metadata_language or "en",
                confidence=metadata_confidence or 0.0,
                detection_source="metadata_fallback",
            )

        # Level 1: Metadata (highest confidence)
        if metadata_language and metadata_confidence and metadata_confidence > 0.8:
            return LanguageDetectionResult(
                primary=metadata_language,
                confidence=metadata_confidence,
                detection_source="provider_metadata",
                dialect=self._detect_dialect(text, metadata_language),
            )

        # Level 2: langdetect library
        if _HAS_LANGDETECT:
            try:
                return self._detect_with_langdetect(text)
            except Exception as exc:
                logger.debug("langdetect failed: %s", exc)

        # Level 3: Character-range heuristics
        heuristic = self._detect_with_heuristics(text)
        if heuristic and heuristic.confidence > 0.7:
            return heuristic

        # Level 4: Keyword-based fallback
        keyword_result = self._detect_with_keywords(text)
        if keyword_result:
            return keyword_result

        # Final fallback
        return LanguageDetectionResult(
            primary=metadata_language or "en",
            confidence=max(metadata_confidence or 0.0, 0.3),
            detection_source="fallback",
        )

    def _detect_with_langdetect(self, text: str) -> LanguageDetectionResult:
        """Level 2: Use langdetect library for accurate detection."""
        sample = text[:5000]  # Limit sample size for performance
        lang = langdetect_detect(sample)

        # Get multiple language probabilities
        try:
            probabilities = langdetect_detect_langs(sample)
            all_langs = {str(p).split(":")[0]: float(str(p).split(":")[1]) for p in probabilities}
            primary = str(probabilities[0]).split(":")[0]
            primary_conf = float(str(probabilities[0]).split(":")[1])
            secondary = [str(p).split(":")[0] for p in probabilities[1:4] if float(str(p).split(":")[1]) > 0.1]
        except Exception:
            all_langs = {lang: 1.0}
            primary_conf = 0.9
            secondary = []

        return LanguageDetectionResult(
            primary=lang,
            secondary=secondary,
            confidence=primary_conf,
            detection_source="langdetect",
            all_languages=all_langs,
        )

    def _detect_with_heuristics(self, text: str) -> LanguageDetectionResult | None:
        """Level 3: Character-range based heuristic detection."""
        text_len = max(len(text), 1)
        detections: list[tuple[str, float]] = []

        for lang, (pattern, min_ratio) in _UNICODE_PATTERNS.items():
            matches = len(re.findall(pattern, text))
            ratio = matches / text_len
            if ratio >= min_ratio:
                detections.append((lang, ratio))

        if not detections:
            # Check if predominantly Latin
            latin = sum(1 for c in text if "A" <= c <= "Z" or "a" <= c <= "z")
            latin_ratio = latin / text_len
            if latin_ratio > 0.8:
                return LanguageDetectionResult(
                    primary="en",
                    confidence=latin_ratio,
                    detection_source="heuristic_latin",
                )
            return None

        detections.sort(key=lambda x: x[1], reverse=True)
        primary = detections[0][0]
        secondary = [d[0] for d in detections[1:]]

        return LanguageDetectionResult(
            primary=primary,
            secondary=secondary,
            confidence=min(detections[0][1] * 3, 0.95),
            detection_source="heuristic_unicode",
            dialect=self._detect_dialect(text, primary),
        )

    def _detect_with_keywords(self, text: str) -> LanguageDetectionResult | None:
        """Level 4: Keyword-based fallback detection."""
        text_lower = text.lower()[:2000]
        words = set(re.findall(r"[a-z]+", text_lower))
        if not words:
            return None

        scores: dict[str, int] = {}
        for lang, keywords in _LANGUAGE_KEYWORDS.items():
            scores[lang] = sum(1 for kw in keywords if kw in words)

        if not scores or max(scores.values()) == 0:
            return None

        best = max(scores, key=scores.get)
        best_score = scores[best]
        total_found = sum(scores.values())

        return LanguageDetectionResult(
            primary=best,
            confidence=min(best_score / max(total_found, 1) * 2, 0.7),
            detection_source="keyword",
        )

    @staticmethod
    def _detect_dialect(text: str, language: str) -> str | None:
        """Detect dialect variant of a language (e.g. en-US, pt-BR)."""
        if language != "en":
            return None
        # Simple heuristic: check for American/British spelling patterns
        us_patterns = ["color", "flavor", "center", "theater", "organize", "realize", "apartment", "elevator", "gasoline", "sidewalk"]
        uk_patterns = ["colour", "flavour", "centre", "theatre", "organise", "realise", "flat", "lift", "petrol", "pavement"]
        text_lower = text.lower()
        us_count = sum(1 for p in us_patterns if p in text_lower)
        uk_count = sum(1 for p in uk_patterns if p in text_lower)
        if us_count > uk_count:
            return "en-US"
        if uk_count > us_count:
            return "en-GB"
        return None

    @staticmethod
    def get_language_name(code: str) -> str:
        """Get human-readable language name from ISO code."""
        return _LANGUAGE_NAMES.get(code, code)
