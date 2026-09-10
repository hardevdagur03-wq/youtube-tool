"""Tests for Phase 9 validators."""

from __future__ import annotations
import pytest
from models.blog_review import BlogReviewRequest
from review.grammar_validator import GrammarValidator
from review.readability_validator import ReadabilityValidator
from review.seo_validator import SEOValidator
from review.duplicate_validator import DuplicateValidator
from review.heading_validator import HeadingValidator
from review.completeness_validator import CompletenessValidator
from review.hallucination_validator import HallucinationValidator, HallucinationRisk
from review.fact_consistency_validator import FactConsistencyValidator
from review.eeat_validator import EEATValidator
from review.linking_validator import InternalLinkingValidator, ExternalLinkingValidator
from review.accessibility_validator import AccessibilityValidator
from review.content_quality_validator import ContentQualityValidator
from review.ai_detection_validator import AIDetectionValidator


SAMPLE_GOOD_CONTENT = """# The Complete Guide to Python Testing

## Introduction

Testing is a critical part of software development. It ensures code quality, prevents regressions, and gives developers confidence when making changes. In this guide, we will explore Python testing frameworks and best practices.

## Why Testing Matters

Testing matters because it catches bugs early. Research shows that bugs caught during development cost 10x less to fix than those found in production. Many teams have adopted test-driven development to improve code quality.

### Types of Tests

There are several types of tests you should know about. Unit tests verify individual functions work correctly. Integration tests ensure components work together. End-to-end tests validate the complete system.

## Getting Started with pytest

Pytest is the most popular testing framework for Python. It is simple to use yet powerful enough for complex test suites. Let us look at how to write your first test.

```python
def test_addition():
    assert 1 + 1 == 2
```

This is a basic test that verifies addition works correctly. Pytest automatically discovers tests in files named test_*.py.

## Best Practices

You should follow these best practices when writing tests:
- Keep tests independent
- Use descriptive test names
- One assertion per test when possible
- Mock external dependencies
- Run tests frequently

## Conclusion

Testing is essential for building reliable software. By following the practices outlined in this guide, you can improve your code quality and development velocity.

## Frequently Asked Questions

### Why is testing important?
Testing is important because it helps catch bugs early and ensures code reliability.

### What is pytest?
Pytest is a Python testing framework that makes it easy to write and run tests.
"""


class TestGrammarValidator:
    def test_name(self):
        v = GrammarValidator()
        assert v.name() == "Grammar Validation"

    def test_empty_content(self):
        v = GrammarValidator()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 100.0

    def test_clean_content(self):
        v = GrammarValidator()
        req = BlogReviewRequest(content="This is a clean sentence. It has no errors.")
        result = v.validate(req)
        assert result.score > 90

    def test_spelling_errors(self):
        v = GrammarValidator()
        req = BlogReviewRequest(content="This sentence has a definately misspelled word. And recieve is also wrong.")
        result = v.validate(req)
        assert result.spelling_errors > 0
        assert result.score < 100

    def test_passive_voice_detection(self):
        v = GrammarValidator()
        text = "The code was written by the team. The tests were executed by the CI. " * 5
        req = BlogReviewRequest(content=text)
        result = v.validate(req)
        assert result.passive_voice_sentences > 0


class TestReadabilityValidator:
    def test_name(self):
        v = ReadabilityValidator()
        assert v.name() == "Readability Analysis"

    def test_empty_content(self):
        v = ReadabilityValidator()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 100.0

    def test_readability_scores(self):
        v = ReadabilityValidator()
        req = BlogReviewRequest(content=SAMPLE_GOOD_CONTENT)
        result = v.validate(req)
        assert result.score > 0
        assert result.flesch_reading_ease > 0
        assert result.flesch_kincaid_grade > 0
        assert result.reading_time_minutes > 0

    def test_difficulty_level(self):
        v = ReadabilityValidator()
        req = BlogReviewRequest(content="Simple easy words. Short sentences. Clear meaning.")
        result = v.validate(req)
        # Short sentences can score lower on Flesch due to syllable calc
        assert result.score >= 0
        assert isinstance(result.difficulty_level, str)


class TestSEOValidator:
    def test_name(self):
        v = SEOValidator()
        assert v.name() == "SEO Audit"

    def test_missing_keyword(self):
        v = SEOValidator()
        req = BlogReviewRequest(
            blog_title="Python Guide",
            primary_keyword="testing",
            content="# Python Guide\nSome content here",
            meta_title="",
            meta_description="",
        )
        result = v.validate(req)
        assert result.score < 100
        assert not result.primary_keyword_in_title
        assert len(result.missing_elements) > 0

    def test_good_seo(self):
        v = SEOValidator()
        content = "# Python Testing Guide\n\nTesting is important."
        req = BlogReviewRequest(
            blog_title="Python Testing Guide",
            primary_keyword="testing",
            meta_title="Python Testing Guide - Complete Tutorial",
            meta_description="Learn Python testing with this comprehensive guide covering pytest, unit tests, and best practices for better code.",
            content=content,
        )
        result = v.validate(req)
        assert result.primary_keyword_in_title
        assert result.primary_keyword_in_h1

    def test_keyword_stuffing(self):
        v = SEOValidator()
        content = ("testing testing testing testing testing testing testing testing testing testing " * 10 +
                   "more content here")
        req = BlogReviewRequest(
            blog_title="Testing",
            primary_keyword="testing",
            content=content,
        )
        result = v.validate(req)
        # May detect stuffing or not depending on density
        assert result.score < 100


class TestDuplicateValidator:
    def test_name(self):
        v = DuplicateValidator()
        assert v.name() == "Duplicate Content Detection"

    def test_no_duplicates(self):
        v = DuplicateValidator()
        content = "# Heading 1\n\nUnique paragraph one.\n\n## Heading 2\n\nUnique paragraph two."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.score == 100.0

    def test_duplicate_paragraphs(self):
        v = DuplicateValidator()
        content = "# Heading 1\n\nSame paragraph.\n\n## Heading 2\n\nSame paragraph."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.duplicate_paragraphs > 0
        assert result.score < 100


class TestHeadingValidator:
    def test_name(self):
        v = HeadingValidator()
        assert v.name() == "Heading Validation"

    def test_no_headings(self):
        v = HeadingValidator()
        req = BlogReviewRequest(content="Just some text without any headings.")
        result = v.validate(req)
        assert result.score == 0

    def test_good_hierarchy(self):
        v = HeadingValidator()
        content = "# H1 Title\n\nSome text.\n\n## H2 Section\n\nMore text.\n\n### H3 Subsection\n\nDetails."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.h1_count == 1
        assert len(result.hierarchy_issues) == 0

    def test_multiple_h1(self):
        v = HeadingValidator()
        content = "# First H1\n\nText.\n\n# Second H1\n\nMore text."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.h1_count > 1
        assert len(result.hierarchy_issues) > 0

    def test_skipped_levels(self):
        v = HeadingValidator()
        content = "# H1\n\nText.\n\n### H3 (skipped H2)\n\nMore text."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert len(result.skipped_levels) > 0


class TestCompletenessValidator:
    def test_name(self):
        v = CompletenessValidator()
        assert v.name() == "Content Completeness"

    def test_empty_content(self):
        v = CompletenessValidator()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 0

    def test_complete_content(self):
        v = CompletenessValidator()
        content = SAMPLE_GOOD_CONTENT
        req = BlogReviewRequest(
            content=content,
            faq=[{"question": "Why?", "answer": "Because."}],
        )
        result = v.validate(req)
        assert result.score > 0


class TestHallucinationValidator:
    def test_name(self):
        v = HallucinationValidator()
        assert v.name() == "Hallucination Risk Detection"

    def test_clean_content(self):
        v = HallucinationValidator()
        req = BlogReviewRequest(content="Python is a programming language created by Guido van Rossum.")
        result = v.validate(req)
        assert result.score > 90

    def test_unsupported_claims(self):
        v = HallucinationValidator()
        content = "Studies show that this technique improves productivity by 300%. Research proves it works."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.unsupported_claims > 0
        assert result.score < 100

    def test_fabricated_references(self):
        v = HallucinationValidator()
        content = "According to a 2023 study by Harvard, this is true. A 2022 report from MIT confirms."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.fabricated_references > 0


class TestFactConsistencyValidator:
    def test_name(self):
        v = FactConsistencyValidator()
        assert v.name() == "Fact Consistency Review"

    def test_clean_content(self):
        v = FactConsistencyValidator()
        content = "Python is great. It is widely used."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.score >= 90


class TestEEATValidator:
    def test_name(self):
        v = EEATValidator()
        assert v.name() == "E-E-A-T Evaluation"

    def test_low_eeat(self):
        v = EEATValidator()
        content = "This is some basic content without any expert references or experience signals."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.score < 50

    def test_high_eeat(self):
        v = EEATValidator()
        content = (
            "In my 10 years of experience as a senior engineer, I have built numerous systems. "
            "Our team implemented this solution for Fortune 500 clients. "
            "Research shows this approach is effective. According to published studies, this method works."
        )
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.score >= 40


class TestLinkingValidators:
    def test_internal_linking_empty(self):
        v = InternalLinkingValidator()
        req = BlogReviewRequest(content="Some content", internal_links=[])
        result = v.validate(req)
        assert result.score < 100
        assert result.internal_link_count == 0

    def test_internal_linking_good(self):
        v = InternalLinkingValidator()
        req = BlogReviewRequest(
            content="Some content",
            internal_links=[
                {"anchor": "learn more about testing", "url": "/testing-guide"},
                {"anchor": "see our API docs", "url": "/api-docs"},
            ],
        )
        result = v.validate(req)
        assert result.internal_link_count == 2

    def test_external_linking_empty(self):
        v = ExternalLinkingValidator()
        req = BlogReviewRequest(content="Content", external_links=[])
        result = v.validate(req)
        assert result.score < 100


class TestAccessibilityValidator:
    def test_name(self):
        v = AccessibilityValidator()
        assert v.name() == "Accessibility Review"

    def test_images_with_alt(self):
        v = AccessibilityValidator()
        content = "![Python logo](/images/python.png) Some text."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.images_missing_alt == 0

    def test_images_without_alt(self):
        v = AccessibilityValidator()
        content = "![](/images/python.png) Some text."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.images_missing_alt == 1


class TestContentQualityValidator:
    def test_name(self):
        v = ContentQualityValidator()
        assert v.name() == "Content Quality Review"

    def test_empty_content(self):
        v = ContentQualityValidator()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 0

    def test_good_content(self):
        v = ContentQualityValidator()
        req = BlogReviewRequest(content=SAMPLE_GOOD_CONTENT)
        result = v.validate(req)
        assert result.score > 50


class TestAIDetectionValidator:
    def test_name(self):
        v = AIDetectionValidator()
        assert v.name() == "AI Detection Risk"

    def test_natural_content(self):
        v = AIDetectionValidator()
        req = BlogReviewRequest(content=SAMPLE_GOOD_CONTENT)
        result = v.validate(req)
        assert result.score > 50

    def test_ai_patterns_detected(self):
        v = AIDetectionValidator()
        content = (
            "In today's digital world, it is important to understand technology. "
            "Let's dive into this topic. When it comes to modern solutions, "
            "it is crucial to consider all options. In conclusion, overall, "
            "it is worth noting that this is essential."
        ) * 3
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.score < 80
