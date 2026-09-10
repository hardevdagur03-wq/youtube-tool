from __future__ import annotations

import pytest


class TestTranscriptValidator:
    def test_valid_transcript(self):
        from validators import transcript_validator as tv
        data = {"plain_text": "Python is a programming language. It is used widely.", "segments": [{"text": "Python is a programming language.", "start": 0.0, "duration": 5.0}]}
        tv.validate_segments(data["segments"])
        tv.validate_text(data["plain_text"])

    def test_empty_transcript(self):
        from validators import transcript_validator as tv
        from exceptions.processing_errors import EmptyTranscriptError
        data = {"plain_text": "", "segments": []}
        with pytest.raises(EmptyTranscriptError):
            tv.validate_segments(data["segments"])

    def test_transcript_too_short(self):
        from validators import transcript_validator as tv
        data = {"plain_text": "Hi", "segments": [{"text": "Hi", "start": 0.0}]}
        tv.validate_text(data["plain_text"])
        tv.validate_segments(data["segments"])

    def test_missing_segments(self):
        from validators import transcript_validator as tv
        from exceptions.processing_errors import EmptyTranscriptError
        data = {"plain_text": "Some text"}
        with pytest.raises(EmptyTranscriptError):
            tv.validate_segments(data.get("segments", []))

    def test_quality_score(self):
        from validators import transcript_validator as tv
        data = {"plain_text": "Python is a programming language used for data science and machine learning applications." * 3, "segments": [{"text": "Test", "start": 0.0} for _ in range(10)]}
        tv.validate_segments(data["segments"])
        tv.validate_text(data["plain_text"])

    def test_quality_score_empty(self):
        from validators import transcript_validator as tv
        from exceptions.processing_errors import EmptyTranscriptError
        data = {"plain_text": "", "segments": []}
        with pytest.raises(EmptyTranscriptError):
            tv.validate_segments(data["segments"])


class TestSEOValidator:
    def test_validate_empty(self):
        from seo_intelligence.seo_validator import SEOValidator
        from seo_intelligence.seo_models import SEOPlan
        validator = SEOValidator()
        plan = SEOPlan()
        issues = validator.validate(plan)
        assert len(issues) > 0

    def test_validate_populated(self):
        from seo_intelligence.seo_validator import SEOValidator
        from seo_intelligence.seo_models import SEOPlan, KeywordInfo, KeywordType, HeadingSuggestion, FAQItem, SchemaMarkup, SchemaType
        validator = SEOValidator()
        plan = SEOPlan()
        plan.keyword_strategy.primary_keyword = "Python"
        plan.keyword_strategy.secondary_keywords = [KeywordInfo(keyword="ds", type=KeywordType.SECONDARY) for _ in range(5)]
        plan.url.suggested_slug = "python-guide"
        plan.meta.meta_title = "Python Guide"
        plan.meta.meta_description = "A" * 140
        plan.heading_strategy.h1 = "Python Guide"
        plan.heading_strategy.h2_suggestions = [HeadingSuggestion(tag="h2", text=f"H2 {i}", order=i) for i in range(5)]
        plan.faqs = [FAQItem(question=f"Q{i}", answer="A") for i in range(3)]
        plan.schemas = [SchemaMarkup(type=SchemaType.ARTICLE)]
        plan.content_strategy.recommended_word_count = 1500
        issues = validator.validate(plan)
        critical = [i for i in issues if "No " in i]
        assert len(critical) == 0


class TestOutlineValidator:
    def test_validate_empty(self):
        from outline_generator.outline_validator import OutlineValidator
        from outline_generator.outline_models import ContentOutline
        validator = OutlineValidator()
        issues = validator.validate(ContentOutline())
        assert len(issues) > 0

    def test_validate_populated(self):
        from outline_generator.outline_validator import OutlineValidator
        from outline_generator.outline_models import ContentOutline, SectionPlan, CTAInfo, FAQPlan
        validator = OutlineValidator()
        o = ContentOutline()
        o.title.primary_title = "Python Guide"
        o.sections = [SectionPlan(heading=f"S{i}", heading_tag="h2", goal="G", order=i) for i in range(5)]
        o.intro_plan.hook_approach = "Hook"
        o.ctas.append(CTAInfo(type="primary", text="Click"))
        o.faqs.append(FAQPlan(question="Q?"))
        o.word_count_plan.total_target = 2000
        issues = validator.validate(o)
        critical = [i for i in issues if "no " in i.lower()]
        assert len(critical) <= 2


class TestSectionValidator:
    def test_validate_empty_section(self):
        from section_generation.section_validator import SectionValidator
        from section_generation.section_models import SectionOutput, SectionType
        validator = SectionValidator()
        output = SectionOutput(section_id="empty", section_type=SectionType.BODY, heading="Empty", content="")
        validation = validator.validate(output)
        assert not validation.valid

    def test_validate_valid_section(self):
        from section_generation.section_validator import SectionValidator
        from section_generation.section_models import SectionOutput, SectionType
        validator = SectionValidator()
        output = SectionOutput(section_id="test", section_type=SectionType.BODY, heading="Test", content="Python is a great language. It is used for data science. Many developers use it. The syntax is clean.", order=1)
        validation = validator.validate(output)
        assert validation.score >= 50 or validation.valid


class TestDraftValidator:
    def test_validate_valid(self):
        from draft.document_validator import DocumentValidator
        from draft.draft_models import DiscoveredSection
        validator = DocumentValidator()
        section = DiscoveredSection(section_id="intro", content="# Valid\n\nThis is valid content with enough words to pass the validation check correctly now.\n")
        result = validator.validate_section(section)
        assert result.exists
        assert result.valid

    def test_validate_empty(self):
        from draft.document_validator import DocumentValidator
        from draft.draft_models import DiscoveredSection
        validator = DocumentValidator()
        section = DiscoveredSection(section_id="empty", content="")
        result = validator.validate_section(section)
        assert not result.exists


class TestOptimizationValidator:
    def test_validate(self):
        from optimization.optimization_validator import OptimizationValidator
        validator = OptimizationValidator()
        from optimization.optimization_models import OptimizationContext, OptimizationType
        result = validator.validate("Original content.", "Optimized content.", OptimizationContext(), [OptimizationType.GRAMMAR])
        assert isinstance(result[0], bool)


class TestExportValidator:
    def test_validate_request(self):
        from export_engine.models import ExportRequest
        req = ExportRequest(channel_input="@test")
        assert req.channel_input == "@test"
        assert req.limit == 0


class TestReviewBaseValidator:
    def test_base_validator_import(self):
        from review.base import BaseValidator
        assert BaseValidator is not None
