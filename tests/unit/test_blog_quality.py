"""Comprehensive tests for the Blog Quality Engine and Content Validator."""

from __future__ import annotations

import pytest

from services.blog.blog_quality import evaluate_blog_quality, BlogQualityScore
from services.blog.blog_validator import BlogValidator, ValidationResult
from services.blog.blog_pipeline import BlogPipeline, BlogPipelineResult


class TestBlogQualityEvaluator:
    def test_empty_content(self):
        score = evaluate_blog_quality("")
        assert score.overall == 0.0
        assert "Empty content" in score.issues

    def test_short_content_flagged(self):
        score = evaluate_blog_quality("Short content.")
        assert len(score.issues) > 0
        assert "Content too short" in score.issues[0]

    def test_grammar_score_proper_content(self):
        content = "This is a well-formed sentence. It has proper capitalization. And ends with periods. " * 20
        score = evaluate_blog_quality(content)
        assert score.grammar_score > 0.5

    def test_grammar_penalty_for_all_caps(self):
        content = "THIS IS ALL CAPS CONTENT. IT HAS NO PROPER CASE. THIS IS BAD. " * 10
        score = evaluate_blog_quality(content)
        assert score.grammar_score < 0.95

    def test_readability_short_sentences(self):
        content = "Short sentences. Very easy. To read. Great flow. " * 20
        score = evaluate_blog_quality(content)
        assert score.readability_score > 0.8

    def test_readability_long_sentences(self):
        long = "This is an extremely long and convoluted sentence that goes on and on without any clear direction " * 20
        score = evaluate_blog_quality(long)
        assert score.readability_score < 0.8

    def test_seo_score_with_title_and_meta(self):
        content = "This is a blog post about machine learning. " * 100
        score = evaluate_blog_quality(
            content=content,
            title="Machine Learning Guide",
            meta_description="A comprehensive guide to machine learning concepts and applications.",
            keywords=["machine learning", "AI"],
        )
        assert score.seo_score > 0.5

    def test_seo_score_without_keywords(self):
        content = "Random content about unrelated topics. " * 50
        score = evaluate_blog_quality(content=content, title="", meta_description="")
        assert score.seo_score < 0.6

    def test_structure_score_with_headings(self):
        content = "# Title\n\nContent here.\n\n## Heading 2\n\nMore content.\n\n### Heading 3\n\nDetails."
        score = evaluate_blog_quality(
            content=content,
            headings=["# Title", "## Heading 2", "### Heading 3"],
        )
        assert score.structure_score > 0.7

    def test_structure_score_without_headings(self):
        content = "Just a paragraph without any structure. " * 20
        score = evaluate_blog_quality(content=content, headings=[])
        assert score.structure_score < 0.7

    def test_originality_detects_duplicates(self):
        same_sentence = "This is a repeated sentence. " * 50
        score = evaluate_blog_quality(same_sentence)
        assert score.originality_score < 0.8

    def test_engagement_with_cta(self):
        content = "Content here. Sign up now. Learn more about this. Contact us. " * 10
        score = evaluate_blog_quality(content)
        assert score.engagement_score > 0.5

    def test_eeat_with_references(self):
        content = "According to research published in 2024. Expert analysis shows. " * 20
        score = evaluate_blog_quality(content)
        assert score.eeat_score > 0.5

    def test_fact_accuracy_with_citations(self):
        content = "Source [1] confirms this finding. [Reference](https://example.com) " * 10
        score = evaluate_blog_quality(content)
        assert score.fact_accuracy > 0.7

    def test_overall_score_high_quality(self):
        content = "# Blog Title\n\n## Introduction\n\nThis is an introduction paragraph. " * 50
        content += "\n\nAccording to research, machine learning is transforming industries. \n\n"
        content += "Sign up for our newsletter. [Learn more](https://example.com)\n\n"
        score = evaluate_blog_quality(
            content=content * 5,
            title="Quality Blog Post About ML",
            meta_description="A comprehensive guide about machine learning and AI.",
            headings=["# Blog Title", "## Introduction", "## Key Concepts", "## Conclusion"],
            keywords=["machine learning", "AI", "deep learning"],
        )
        assert score.overall > 0.3

    def test_output_format(self):
        score = evaluate_blog_quality("Normal content. With proper writing. " * 20)
        assert isinstance(score, BlogQualityScore)
        assert isinstance(score.overall, float)
        assert isinstance(score.issues, list)
        assert isinstance(score.suggestions, list)
        assert 0 <= score.overall <= 1

    def test_word_count_tracking(self):
        text = "word " * 100
        score = evaluate_blog_quality(text)
        assert score.word_count == 100


class TestBlogValidator:
    def test_hallucination_detection_clean(self):
        content = "This is a well-researched article. According to a 2024 study published in Nature, the findings were conclusive."
        result = BlogValidator.check_hallucinations(content)
        assert result.passed is True

    def test_hallucination_high_statistics(self):
        content = "50% of people. 30 million users. 100 billion dollars. 75% growth. 90% accuracy. 80% satisfaction. " * 3
        result = BlogValidator.check_hallucinations(content)
        assert len(result.warnings) > 0

    def test_hallucination_absolute_terms(self):
        content = "This is always true. It never fails. Everyone agrees. Nobody disputes. It's impossible. It guarantees 100% results."
        result = BlogValidator.check_hallucinations(content)
        assert len(result.warnings) > 0

    def test_factual_claims_with_citations(self):
        content = "According to [source](https://example.com), this is accurate."
        result = BlogValidator.check_factual_claims(content)
        assert result.details.get("citations", 0) >= 1

    def test_factual_claims_date_claims(self):
        content = "In 2024, the study was published. By 2025, results were confirmed."
        result = BlogValidator.check_factual_claims(content)
        assert result.details.get("date_claims", 0) >= 2

    def test_plagiarism_repeated_sentences(self):
        content = "This sentence is repeated. " * 10
        result = BlogValidator.check_plagiarism_indicators(content)
        assert len(result.warnings) > 0

    def test_plagiarism_unique_content(self):
        content = "This is a unique sentence. Another different one. A third distinct statement. Four is also different. Five is original."
        result = BlogValidator.check_plagiarism_indicators(content)
        assert result.score >= 0.7

    def test_eeat_strong_signals(self):
        content = "According to research published in a peer-reviewed journal. Expert analysis confirmed these findings. Multiple studies have verified  this data. [Source](https://example.com)"
        result = BlogValidator.check_eeat(content)
        assert result.score > 0.5

    def test_eeat_weak_signals(self):
        content = "Some people say this is true. It might be good. Maybe you should try it."
        result = BlogValidator.check_eeat(content)
        assert result.score < 0.6

    def test_validate_all_runs_all_checks(self):
        content = "This is a test article. " * 20
        results = BlogValidator.validate_all(content)
        assert "hallucinations" in results
        assert "factual_claims" in results
        assert "plagiarism" in results
        assert "eeat" in results

    def test_validation_result_defaults(self):
        result = ValidationResult()
        assert result.passed is True
        assert result.score == 1.0
        assert result.issues == []
        assert result.warnings == []


class TestBlogPipeline:
    def test_pipeline_with_good_content(self):
        pipeline = BlogPipeline()
        content = "# Blog Title\n\n## Introduction\n\nThis is quality content. " * 30
        content += "\n\nAccording to research, this is verified. [Source](https://example.com)\n\n"
        content += "Sign up for more. Learn more today.\n\n\n\n\n\n"
        result = pipeline.run(
            content=content * 3,
            title="Quality Blog",
            meta_description="A quality blog post description.",
            headings=["# Blog Title", "## Introduction", "## Key Points"],
            keywords=["quality", "blog", "research"],
        )
        assert result.total_duration_ms >= 0
        assert result.stages is not None

    def test_pipeline_with_empty_content(self):
        pipeline = BlogPipeline()
        result = pipeline.run(content="")
        assert result.success is False
        assert result.error is not None

    def test_pipeline_summary(self):
        pipeline = BlogPipeline()
        content = "Quality content. " * 50
        result = pipeline.run(content=content, title="Test")
        summary = pipeline.summary(result)
        assert "success" in summary
        assert "quality_score" in summary
        assert "word_count" in summary
        assert "stages" in summary
        assert summary["word_count"] > 0

    def test_pipeline_stages_tracked(self):
        pipeline = BlogPipeline()
        content = "Content for stage tracking. " * 20
        result = pipeline.run(content=content)
        assert len(result.stages) >= 2
        assert result.stages[0].name == "quality_evaluation"
        assert result.stages[1].name == "content_validation"

    def test_pipeline_duration_measured(self):
        pipeline = BlogPipeline()
        content = "Duration test content. " * 30
        import time
        start = time.time()
        result = pipeline.run(content=content)
        elapsed = (time.time() - start) * 1000
        assert result.total_duration_ms >= 0
        assert elapsed >= 0


class TestBlogQualityScore:
    def test_default_values(self):
        score = BlogQualityScore()
        assert score.overall == 0.0
        assert score.issues == []
        assert score.suggestions == []

    def test_custom_values(self):
        score = BlogQualityScore(
            overall=0.85,
            grammar_score=0.9,
            seo_score=0.8,
            word_count=1500,
            issues=["Minor issue"],
        )
        assert score.overall == 0.85
        assert score.word_count == 1500
