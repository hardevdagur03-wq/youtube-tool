from __future__ import annotations

import pytest


class TestBaseProcessor:
    def test_process(self):
        from pipeline.base_processor import BaseProcessor
        from models.processing_result import ProcessingStepName

        class _Concrete(BaseProcessor):
            step_name = ProcessingStepName.NORMALIZE_UNICODE
            def process(self, context):
                context["text"] = context.get("text", "").strip()
                return context

        processor = _Concrete()
        result = processor.process({"text": "Python is a programming language."})
        assert result is not None

    def test_process_empty(self):
        from pipeline.base_processor import BaseProcessor
        from models.processing_result import ProcessingStepName

        class _Concrete(BaseProcessor):
            step_name = ProcessingStepName.NORMALIZE_UNICODE
            def process(self, context):
                context["text"] = context.get("text", "").strip()
                return context

        processor = _Concrete()
        result = processor.process({"text": ""})
        assert result is not None or result == ""

    def test_process_none(self):
        from pipeline.base_processor import BaseProcessor
        from models.processing_result import ProcessingStepName

        class _Concrete(BaseProcessor):
            step_name = ProcessingStepName.NORMALIZE_UNICODE
            def process(self, context):
                text = context.get("text")
                context["text"] = (text or "").strip()
                return context

        processor = _Concrete()
        result = processor.process({"text": None})
        assert result is not None


class TestCaptionMerger:
    def test_merge(self):
        from pipeline.caption_merger import CaptionMerger
        merger = CaptionMerger()
        captions = [
            {"text": "Python is", "start": 0.0, "duration": 1.0},
            {"text": "a programming language", "start": 1.0, "duration": 1.5},
            {"text": "used for data science", "start": 2.5, "duration": 2.0},
        ]
        result = merger.process({"segments": captions})
        assert result is not None
        assert len(result.get("text", "")) > 0

    def test_merge_empty(self):
        from pipeline.caption_merger import CaptionMerger
        merger = CaptionMerger()
        result = merger.process({"segments": []})
        assert result.get("text", "") == ""

    def test_merge_with_gap(self):
        from pipeline.caption_merger import CaptionMerger
        merger = CaptionMerger()
        captions = [
            {"text": "First", "start": 0.0, "duration": 1.0},
            {"text": "Second", "start": 10.0, "duration": 1.0},
        ]
        result = merger.process({"segments": captions})
        text = result.get("text", "")
        assert len(text) >= 1


class TestFillerProcessor:
    def test_remove_fillers(self):
        from pipeline.filler_processor import FillerProcessor
        processor = FillerProcessor(remove_fillers=True)
        result = processor.process({"text": "um so like Python is uh basically great"})
        text = result.get("text", "")
        assert "um" not in text
        assert "uh" not in text
        assert "like" not in text

    def test_no_fillers(self):
        from pipeline.filler_processor import FillerProcessor
        processor = FillerProcessor(remove_fillers=True)
        result = processor.process({"text": "Python is a great programming language"})
        assert result.get("text", "") == "Python is a great programming language"

    def test_empty(self):
        from pipeline.filler_processor import FillerProcessor
        processor = FillerProcessor(remove_fillers=True)
        result = processor.process({"text": ""})
        assert result.get("text", "") == ""


class TestPunctuationProcessor:
    def test_add_punctuation(self):
        from pipeline.punctuation_processor import PunctuationProcessor
        processor = PunctuationProcessor()
        result = processor.process({"text": "Python is great\nIt is used widely"})
        assert result.get("text", "").count(".") > 0

    def test_already_punctuated(self):
        from pipeline.punctuation_processor import PunctuationProcessor
        processor = PunctuationProcessor()
        result = processor.process({"text": "Python is great. It is used widely."})
        assert result.get("text", "").count(".") >= 2

    def test_empty(self):
        from pipeline.punctuation_processor import PunctuationProcessor
        processor = PunctuationProcessor()
        result = processor.process({"text": ""})
        assert result.get("text", "") == ""


class TestTimestampProcessor:
    def test_process_removes_timestamps(self):
        from pipeline.timestamp_processor import TimestampProcessor
        processor = TimestampProcessor()
        result = processor.process({"text": "00:00:05 Python is great 01:30:00"})
        text = result.get("text", "")
        assert "00:00:05" not in text
        assert "Python" in text

    def test_empty(self):
        from pipeline.timestamp_processor import TimestampProcessor
        processor = TimestampProcessor()
        result = processor.process({"text": ""})
        assert result.get("text", "") == ""


class TestLanguageProcessor:
    def test_detect(self):
        from pipeline.language_processor import LanguageProcessor
        processor = LanguageProcessor()
        result = processor.process({"text": "Python is a programming language"})
        assert result.get("language") is not None

    def test_detect_empty(self):
        from pipeline.language_processor import LanguageProcessor
        processor = LanguageProcessor()
        result = processor.process({"text": ""})
        assert result.get("language") is None


class TestParagraphProcessor:
    def test_build_paragraphs(self):
        from pipeline.paragraph_processor import ParagraphProcessor
        processor = ParagraphProcessor()
        result = processor.process({"text": "Python is great. It is used for data science. Many developers use it."})
        paragraphs = result.get("paragraphs", [])
        assert len(paragraphs) > 0

    def test_build_empty(self):
        from pipeline.paragraph_processor import ParagraphProcessor
        processor = ParagraphProcessor()
        result = processor.process({"text": ""})
        assert result.get("paragraphs", []) == []


class TestCapitalizationProcessor:
    def test_capitalize(self):
        from pipeline.capitalization_processor import CapitalizationProcessor
        processor = CapitalizationProcessor()
        result = processor.process({"text": "python is great. it is used widely. data science is popular."})
        text = result.get("text", "")
        assert "Python" in text
        assert "It" in text
        assert "Data" in text

    def test_already_capitalized(self):
        from pipeline.capitalization_processor import CapitalizationProcessor
        processor = CapitalizationProcessor()
        text = "Python is great. It is used widely."
        result = processor.process({"text": text})
        assert result.get("text", "") == text

    def test_empty(self):
        from pipeline.capitalization_processor import CapitalizationProcessor
        processor = CapitalizationProcessor()
        result = processor.process({"text": ""})
        assert result.get("text", "") == ""


class TestQualityChecker:
    def test_check(self):
        from pipeline.quality_checker import QualityChecker
        checker = QualityChecker()
        result = checker.process({"text": "Python is a programming language used for data science and machine learning."})
        flags = result.get("flags")
        assert flags is not None
        assert hasattr(flags, "quality_passed")

    def test_check_empty(self):
        from pipeline.quality_checker import QualityChecker
        checker = QualityChecker()
        result = checker.process({"text": ""})
        flags = result.get("flags")
        assert flags is not None

    def test_check_short(self):
        from pipeline.quality_checker import QualityChecker
        checker = QualityChecker()
        result = checker.process({"text": "Hi"})
        assert result is not None


class TestProcessingPipeline:
    def test_full_pipeline(self):
        from pipeline.processing_pipeline import ProcessingPipeline
        pipeline = ProcessingPipeline()
        segments = [{"text": "um so Python is uh a great language for data science it is used widely"}]
        result = pipeline.run(segments, remove_fillers=True)
        assert result is not None
        text = result.get("text", "")
        assert "um" not in text
        assert "Python" in text

    def test_pipeline_empty_input(self):
        from pipeline.processing_pipeline import ProcessingPipeline
        pipeline = ProcessingPipeline()
        result = pipeline.run([])
        assert result is not None

    def test_pipeline_with_segments(self):
        from pipeline.processing_pipeline import ProcessingPipeline
        pipeline = ProcessingPipeline()
        segments = [{"text": "Python is great"}, {"text": "It is used widely"}]
        result = pipeline.run(segments)
        assert result.get("text") is not None

    def test_pipeline_steps(self):
        from pipeline.processing_pipeline import ProcessingPipeline
        pipeline = ProcessingPipeline()
        result = pipeline.run([{"text": "test"}])
        steps = result.get("steps", [])
        assert len(steps) > 0
