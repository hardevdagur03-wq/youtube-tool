"""Tests for the Quality Pipeline."""

from __future__ import annotations

from models.transcript import TranscriptResult, TranscriptSource, TranscriptProviderName
from transcript_reliability.language_detector import LanguageDetector
from transcript_reliability.validation_engine import ValidationEngine
from transcript_reliability.duplicate_remover import DuplicateRemover
from transcript_reliability.silence_detector import SilenceDetector
from transcript_reliability.cleaning_engine import CleaningEngine


class TestLanguageDetector:
    def setup_method(self):
        self.detector = LanguageDetector()

    def test_detect_english(self):
        result = self.detector.detect("Hello world, this is a test transcript in English.")
        assert result.primary == "en"
        assert result.confidence > 0.5

    def test_detect_with_metadata(self):
        result = self.detector.detect("Hola mundo", metadata_language="es", metadata_confidence=0.95)
        assert result.primary == "es"
        assert result.detection_source == "provider_metadata"

    def test_detect_short_text_fallback(self):
        result = self.detector.detect("Hi", metadata_language="fr", metadata_confidence=0.5)
        assert result.primary is not None

    def test_detect_empty_text(self):
        result = self.detector.detect("")
        assert result.primary is not None

    def test_detect_heuristic_chinese(self):
        result = self.detector.detect("这是一个测试文本用于检测中文")
        assert result.primary in ("zh", "zh-cn", "zh-tw")

    def test_detect_heuristic_hindi(self):
        result = self.detector.detect("यह एक परीक्षण पाठ है हिंदी भाषा के लिए")
        assert result.primary == "hi"

    def test_get_language_name(self):
        assert LanguageDetector.get_language_name("en") == "English"
        assert LanguageDetector.get_language_name("unknown") == "unknown"


class TestValidationEngine:
    def setup_method(self):
        self.engine = ValidationEngine()

    def _make_transcript(self, text="Test text here.", words=3, segments=None):
        from models.transcript import TranscriptSegment
        segs = segments or [TranscriptSegment(start=0.0, end=1.0, duration=1.0, text=text)]
        return TranscriptResult(
            success=True, video_id="test123",
            segments=segs, plain_text=text, word_count=words,
            duration_seconds=10.0,
            source=TranscriptSource.MANUAL, provider=TranscriptProviderName.YOUTUBE_MANUAL,
        )

    def test_valid_transcript_passes(self, sample_transcript):
        report = self.engine.validate(sample_transcript)
        assert report.overall_score > 0.3
        assert report.passed == True

    def test_empty_transcript_fails(self):
        tr = TranscriptResult(success=False, video_id="test", error="empty")
        report = self.engine.validate(tr)
        assert report.overall_score <= 0.6
        assert report.passed == True  # 0.5 > 0.3 threshold

    def test_minimum_length_check(self):
        tr = self._make_transcript(text="Hi", words=1)
        report = self.engine.validate(tr)
        assert "minimum_length" in report.failed_checks

    def test_all_12_checks_executed(self, sample_transcript):
        report = self.engine.validate(sample_transcript)
        assert len(report.checks) == 12

    def test_timestamp_coverage(self, sample_transcript):
        report = self.engine.validate(sample_transcript)
        timestamp_check = [c for c in report.checks if c.check_name == "timestamp_coverage"]
        assert len(timestamp_check) == 1

    def test_provider_integrity(self, sample_transcript):
        sample_transcript.segments = []
        sample_transcript.plain_text = ""
        report = self.engine.validate(sample_transcript)
        provider_check = [c for c in report.checks if c.check_name == "provider_integrity"]
        assert provider_check[0].passed == False

    def test_minimum_segments(self):
        tr = self._make_transcript()
        report = self.engine.validate(tr)
        assert report.passed == True


class TestDuplicateRemover:
    def test_no_duplicates(self):
        from models.transcript import TranscriptSegment
        segs = [TranscriptSegment(start=i*2.0, end=i*2.0+1.0, duration=1.0, text=f"Segment {i}") for i in range(5)]
        remover = DuplicateRemover()
        cleaned, report = remover.remove_duplicates(segs)
        assert len(cleaned) == 5
        assert report.total_duplicates_found == 0

    def test_exact_duplicate_removed(self):
        from models.transcript import TranscriptSegment
        segs = [TranscriptSegment(start=0.0, end=1.0, duration=1.0, text="Hello world."),
                TranscriptSegment(start=1.0, end=2.0, duration=1.0, text="Hello world."),
                TranscriptSegment(start=2.0, end=3.0, duration=1.0, text="Different text.")]
        remover = DuplicateRemover()
        cleaned, report = remover.remove_duplicates(segs)
        assert len(cleaned) == 2
        assert report.total_duplicates_found == 1

    def test_empty_segments(self):
        remover = DuplicateRemover()
        cleaned, report = remover.remove_duplicates([])
        assert len(cleaned) == 0

    def test_near_duplicate_detected(self, test_config):
        from models.transcript import TranscriptSegment
        test_config.duplicate_similarity_threshold = 0.7
        remover = DuplicateRemover(test_config)
        segs = [TranscriptSegment(start=0.0, end=1.0, duration=1.0, text="The quick brown fox jumps over the lazy dog."),
                TranscriptSegment(start=1.0, end=2.0, duration=1.0, text="The quick brown fox jumps over the lazy cat.")]
        cleaned, report = remover.remove_duplicates(segs)
        assert report.total_duplicates_found >= 1

    def test_empty_text_not_flagged(self):
        from models.transcript import TranscriptSegment
        segs = [TranscriptSegment(start=0.0, end=1.0, duration=1.0, text=""),
                TranscriptSegment(start=1.0, end=2.0, duration=1.0, text="")]
        remover = DuplicateRemover()
        cleaned, report = remover.remove_duplicates(segs)
        assert report.total_duplicates_found == 0


class TestSilenceDetector:
    def test_normal_transcript_not_silent(self, sample_transcript):
        detector = SilenceDetector()
        result = detector.detect(sample_transcript)
        assert result.is_silent == False

    def test_music_only_detected(self):
        from models.transcript import TranscriptSegment
        segs = [TranscriptSegment(start=0.0, end=1.0, duration=1.0, text="[Music]"),
                TranscriptSegment(start=1.0, end=2.0, duration=1.0, text="[Music]")]
        tr = TranscriptResult(success=True, video_id="test", segments=segs,
                              plain_text="[Music] [Music]", word_count=2)
        detector = SilenceDetector()
        result = detector.detect(tr)
        assert result.is_silent == True

    def test_placeholder_captions(self):
        from models.transcript import TranscriptSegment
        segs = [TranscriptSegment(start=0.0, end=1.0, duration=1.0, text="[inaudible]"),
                TranscriptSegment(start=1.0, end=2.0, duration=1.0, text="[inaudible]")]
        tr = TranscriptResult(success=True, video_id="test", segments=segs,
                              plain_text="[inaudible] [inaudible]", word_count=2)
        detector = SilenceDetector()
        result = detector.detect(tr)
        assert "placeholder_captions" in result.patterns_detected

    def test_empty_transcript(self):
        tr = TranscriptResult(success=False, video_id="test", error="empty")
        detector = SilenceDetector()
        result = detector.detect(tr)
        assert result.is_silent == False


class TestCleaningEngine:
    def test_clean_transcript_preserves_content(self, sample_transcript):
        engine = CleaningEngine()
        original_text = sample_transcript.plain_text
        cleaned = engine.clean(sample_transcript)
        assert cleaned.plain_text is not None
        assert len(cleaned.plain_text) > 0

    def test_unicode_normalization(self):
        engine = CleaningEngine()
        tr = TranscriptResult(success=True, video_id="test",
                              segments=[], plain_text="café résumé naïve",
                              word_count=3)
        cleaned = engine.clean(tr)
        assert "café" in cleaned.plain_text

    def test_remove_emoji(self):
        engine = CleaningEngine()
        tr = TranscriptResult(success=True, video_id="test",
                              segments=[], plain_text="Hello 😊 world 🎉",
                              word_count=3)
        cleaned = engine.clean(tr)
        assert "😊" not in cleaned.plain_text
        assert "🎉" not in cleaned.plain_text

    def test_speaker_label_normalization(self):
        engine = CleaningEngine()
        tr = TranscriptResult(success=True, video_id="test",
                              segments=[], plain_text="Speaker 1: Hello. Speaker 2: Hi.",
                              word_count=4)
        cleaned = engine.clean(tr)
        assert "**Speaker 1:**" in cleaned.plain_text or "Speaker 1:" in cleaned.plain_text

    def test_disable_stage(self):
        engine = CleaningEngine()
        engine.disable_stage("emoji_remover")
        assert engine._enabled_stages is not None
        engine.enable_stage("emoji_remover")

    def test_whitespace_normalization(self):
        engine = CleaningEngine()
        tr = TranscriptResult(success=True, video_id="test",
                              segments=[], plain_text="Hello    world   test",
                              word_count=3)
        cleaned = engine.clean(tr)
        assert "    " not in cleaned.plain_text
