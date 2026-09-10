from __future__ import annotations

from models.blog_review import BlogReviewRequest, IssueSeverity, ReviewIssue
from review.review_models_ext import ReviewReport


class TestReviewModels:
    def test_review_models_import(self):
        issue = ReviewIssue(severity=IssueSeverity.HIGH, description="Test issue")
        assert issue.description == "Test issue"
        assert issue.severity == IssueSeverity.HIGH

    def test_review_result(self):
        result = ReviewReport()
        assert result.publication_status.overall_score == 0.0


class TestContentQualityValidator:
    def test_validate(self):
        from review.content_quality_validator import ContentQualityValidator
        validator = ContentQualityValidator()
        request = BlogReviewRequest(content="This is a sample document with enough content for quality validation purposes. It has multiple sentences. And covers various aspects.")
        result = validator.validate(request)
        assert result.score >= 0


class TestCompletenessValidator:
    def test_validate(self):
        from review.completeness_validator import CompletenessValidator
        validator = CompletenessValidator()
        request = BlogReviewRequest(content="# Intro\n\nContent\n\n## Body\n\nContent\n\n## Conclusion\n\nContent\n")
        result = validator.validate(request)
        assert result.score >= 0


class TestFactConsistencyValidator:
    def test_validate(self):
        from review.fact_consistency_validator import FactConsistencyValidator
        validator = FactConsistencyValidator()
        request = BlogReviewRequest(content="Python is a programming language. Python was created in 1991.")
        result = validator.validate(request)
        assert result.score >= 0


class TestGrammarValidator:
    def test_validate(self):
        from review.grammar_validator import GrammarValidator
        validator = GrammarValidator()
        request = BlogReviewRequest(content="This is a correct sentence. Python is great.")
        result = validator.validate(request)
        assert result.score >= 0


class TestHallucinationValidator:
    def test_validate(self):
        from review.hallucination_validator import HallucinationValidator
        validator = HallucinationValidator()
        request = BlogReviewRequest(content="Python is a programming language created in 1991.")
        result = validator.validate(request)
        assert result.score >= 0


class TestHeadingValidator:
    def test_validate(self):
        from review.heading_validator import HeadingValidator
        validator = HeadingValidator()
        request = BlogReviewRequest(content="# Title\n\n## Section 1\n\nContent\n\n## Section 2\n\nContent\n")
        result = validator.validate(request)
        assert result.score >= 0

    def test_validate_no_headings(self):
        from review.heading_validator import HeadingValidator
        validator = HeadingValidator()
        request = BlogReviewRequest(content="Plain text without any headings.")
        result = validator.validate(request)
        assert result.score < 50


class TestReadabilityValidator:
    def test_validate(self):
        from review.readability_validator import ReadabilityValidator
        validator = ReadabilityValidator()
        request = BlogReviewRequest(content="Python is easy to read. The syntax is clear. Developers love it. It is simple and powerful.")
        result = validator.validate(request)
        assert result.score >= 0


class TestSEOAutoValidator:
    def test_validate(self):
        from review.seo_validator import SEOValidator as SEOAutoValidator
        validator = SEOAutoValidator()
        request = BlogReviewRequest(content="Python is the best programming language for data science. Python offers many libraries.", primary_keyword="Python")
        result = validator.validate(request)
        assert result.score >= 0


class TestDuplicateValidator:
    def test_validate(self):
        from review.duplicate_validator import DuplicateValidator
        validator = DuplicateValidator()
        request = BlogReviewRequest(content="Python is great.\n\nPython is great.\n\nPython is great.\n\nPython is great.\n\nPython is great.")
        result = validator.validate(request)
        assert result.score <= 100


class TestMarkdownValidator:
    def test_validate(self):
        from review.markdown_validator import MarkdownValidator
        validator = MarkdownValidator()
        request = BlogReviewRequest(content="# Title\n\n## Section\n\nContent\n\n- List item\n")
        result = validator.validate(request)
        assert result.score >= 0


class TestTableValidator:
    def test_validate(self):
        from review.table_validator import TableValidator
        validator = TableValidator()
        request = BlogReviewRequest(content="| H1 | H2 |\n|----|----|\n| A | B |\n")
        result = validator.validate(request)
        assert result.score >= 0


class TestImageValidator:
    def test_validate(self):
        from review.image_validator import ImageValidator
        validator = ImageValidator()
        request = BlogReviewRequest(content="![alt](image.png)\n\n![alt2](image2.jpg)\n")
        result = validator.validate(request)
        assert result.score >= 0


class TestLinkingValidator:
    def test_validate(self):
        from review.linking_validator import InternalLinkingValidator
        validator = InternalLinkingValidator()
        request = BlogReviewRequest(content="[link](https://example.com)\n\n[another](https://test.com)\n")
        result = validator.validate(request)
        assert result.score >= 0


class TestAIDetectionValidator:
    def test_validate(self):
        from review.ai_detection_validator import AIDetectionValidator
        validator = AIDetectionValidator()
        request = BlogReviewRequest(content="Python is a versatile programming language that empowers developers.")
        result = validator.validate(request)
        assert result.score >= 0


class TestAccessibilityValidator:
    def test_validate(self):
        from review.accessibility_validator import AccessibilityValidator
        validator = AccessibilityValidator()
        request = BlogReviewRequest(content="![Python logo](logo.png)\n\nContent.\n")
        result = validator.validate(request)
        assert result.score >= 0


class TestEEATValidator:
    def test_validate(self):
        from review.eeat_validator import EEATValidator
        validator = EEATValidator()
        request = BlogReviewRequest(content="Python is a programming language. It was created by Guido van Rossum. It is used by experts worldwide.")
        result = validator.validate(request)
        assert result.score >= 0


class TestPassiveVoiceDetector:
    def test_validate(self):
        from review.passive_voice_detector import PassiveVoiceDetector
        detector = PassiveVoiceDetector()
        request = BlogReviewRequest(content="Python was created by Guido van Rossum. The code was written by the developer.")
        result = detector.validate(request)
        assert result.passive_voice_sentences >= 0

    def test_validate_no_passive(self):
        from review.passive_voice_detector import PassiveVoiceDetector
        detector = PassiveVoiceDetector()
        request = BlogReviewRequest(content="Python creates amazing applications. Developers write clean code.")
        result = detector.validate(request)
        assert result.passive_voice_sentences == 0


class TestRecordAnalyzer:
    def test_validate(self):
        from review.keyword_analyzer import KeywordAnalyzer
        analyzer = KeywordAnalyzer()
        request = BlogReviewRequest(content="Python is great for data science. Python offers many tools. Data science is popular.", primary_keyword="Python")
        result = analyzer.validate(request)
        assert isinstance(result.score, float)


class TestReviewScorer:
    def test_compute_score(self):
        from review.review_models_ext import QualityScores
        from review.review_scorer import ReviewScorer
        scorer = ReviewScorer()
        scores = QualityScores(grammar=85.0, completeness=90.0, seo=75.0)
        score = scorer.compute(scores)
        assert 0 <= score <= 100


class TestRecommendationEngine:
    def test_generate(self):
        from models.blog_review import QualityReport
        from review.recommendation_engine import RecommendationEngine
        engine = RecommendationEngine()
        report = QualityReport()
        recommendations = engine.generate(report)
        assert len(recommendations) >= 0


class TestReviewReportGenerator:
    def test_generate(self):
        from models.blog_review import BlogReviewRequest, QualityReport
        from review.review_report_generator import ReviewReportGenerator
        generator = ReviewReportGenerator()
        request = BlogReviewRequest(content="test content")
        quality_report = QualityReport()
        report = generator.generate(request=request, quality_report=quality_report)
        assert report.publication_status.overall_score >= 0


class TestReviewPipeline:
    def test_review(self):
        from review.review_pipeline import ReviewPipeline
        pipeline = ReviewPipeline()
        request = BlogReviewRequest(content="Python is a programming language. It was created in 1991. Python is used for data science.", primary_keyword="Python")
        response, report = pipeline.review(request)
        assert response.success
        assert report is not None
        assert report.publication_status.overall_score >= 0
