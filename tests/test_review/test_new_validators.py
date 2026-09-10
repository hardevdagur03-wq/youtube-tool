"""Tests for new review validators (Markdown, Keyword, Passive Voice, Table, Image)."""

from __future__ import annotations
import pytest
from models.blog_review import BlogReviewRequest
from review.markdown_validator import MarkdownValidator
from review.keyword_analyzer import KeywordAnalyzer
from review.passive_voice_detector import PassiveVoiceDetector, PASSIVE_PATTERNS
from review.table_validator import TableValidator
from review.image_validator import ImageValidator


SAMPLE_GOOD_CONTENT = """# The Complete Guide to Python Testing

## Introduction

Testing is a critical part of software development. It ensures code quality, prevents regressions, and gives developers confidence when making changes.

## Why Testing Matters

Testing matters because it catches bugs early. Research shows that bugs caught during development cost 10x less to fix than those found in production.

```python
def test_addition():
    assert 1 + 1 == 2
```

| Feature | Description | Status |
|---------|-------------|--------|
| Unit Tests | Test individual functions | Active |
| Integration | Test component interaction | Active |

![Python Logo](/images/python-logo.png)

## Conclusion

Testing is essential for building reliable software.
"""


class TestMarkdownValidator:
    def test_name(self):
        v = MarkdownValidator()
        assert v.name() == "Markdown Validation"

    def test_empty_content(self):
        v = MarkdownValidator()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 100.0

    def test_good_markdown(self):
        v = MarkdownValidator()
        req = BlogReviewRequest(content=SAMPLE_GOOD_CONTENT)
        result = v.validate(req)
        assert result.score > 50
        assert result.table_count >= 1
        assert result.code_block_count >= 1
        assert result.image_count >= 1

    def test_broken_table(self):
        v = MarkdownValidator()
        content = "| H1 | H2\n|---|----|\n| C1 | C2 | C3"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert len(result.table_issues) > 0

    def test_images_missing_alt(self):
        v = MarkdownValidator()
        content = "![](/img.png) Text."
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.images_missing_alt == 1

    def test_heading_skip(self):
        v = MarkdownValidator()
        content = "# H1\n\n### H3 (skipped H2)"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert len(result.heading_issues) > 0

    def test_multiple_h1(self):
        v = MarkdownValidator()
        content = "# H1\n\n# Second H1"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert len(result.heading_issues) > 0

    def test_code_block_empty(self):
        v = MarkdownValidator()
        content = "```\n\n```"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert len(result.code_block_issues) > 0

    def test_html_usage(self):
        v = MarkdownValidator()
        content = "<div>Hello</div>"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.html_usage_detected is True


class TestKeywordAnalyzer:
    def test_name(self):
        v = KeywordAnalyzer()
        assert v.name() == "Keyword Analysis"

    def test_empty_content(self):
        v = KeywordAnalyzer()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 100.0

    def test_keyword_in_content(self):
        v = KeywordAnalyzer()
        req = BlogReviewRequest(
            blog_title="Python Testing Guide",
            primary_keyword="testing",
            content="# Python Testing Guide\n\nTesting is important. Testing matters.",
        )
        result = v.validate(req)
        assert result.primary_keyword_density > 0
        assert result.keyword_in_title is True

    def test_keyword_not_in_content(self):
        v = KeywordAnalyzer()
        req = BlogReviewRequest(
            blog_title="Random Title",
            primary_keyword="python",
            content="# Something\n\nTotally unrelated content here.",
        )
        result = v.validate(req)
        assert result.primary_keyword_density == 0
        assert result.keyword_in_title is False
        assert len(result.issues) > 0

    def test_keyword_stuffing(self):
        v = KeywordAnalyzer()
        content = "testing testing testing testing testing testing " * 20
        req = BlogReviewRequest(
            blog_title="Testing",
            primary_keyword="testing",
            content=content,
        )
        result = v.validate(req)
        assert result.keyword_stuffing_detected is True or result.score < 100

    def test_secondary_keywords(self):
        v = KeywordAnalyzer()
        req = BlogReviewRequest(
            primary_keyword="python",
            secondary_keywords=["testing", "framework"],
            content="# Python\n\nPython testing with pytest framework.",
        )
        result = v.validate(req)
        assert "testing" in result.secondary_keyword_density
        assert "framework" in result.secondary_keyword_density


class TestPassiveVoiceDetector:
    def test_name(self):
        v = PassiveVoiceDetector()
        assert v.name() == "Passive Voice Detection"

    def test_empty_content(self):
        v = PassiveVoiceDetector()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 100.0

    def test_no_passive_voice(self):
        v = PassiveVoiceDetector()
        req = BlogReviewRequest(content="The team wrote the code. The developer fixed the bug. I tested the feature.")
        result = v.validate(req)
        assert result.score > 80

    def test_passive_voice_detected(self):
        v = PassiveVoiceDetector()
        req = BlogReviewRequest(content="The code was written by the team. The tests were executed by the CI.")
        result = v.validate(req)
        assert result.passive_voice_sentences > 0
        assert result.score < 100

    def test_weak_verb_constructions(self):
        v = PassiveVoiceDetector()
        req = BlogReviewRequest(content="There are many reasons why this is important.")
        result = v.validate(req)
        assert result.grammar_errors > 0 or result.score < 100

    def test_weak_adverbs(self):
        v = PassiveVoiceDetector()
        req = BlogReviewRequest(content="This is very important and really useful. It is quite good.")
        result = v.validate(req)
        assert result.run_on_sentences > 0 or result.score < 100

    def test_passive_patterns_defined(self):
        assert len(PASSIVE_PATTERNS) >= 6


class TestTableValidator:
    def test_name(self):
        v = TableValidator()
        assert v.name() == "Table Validation"

    def test_empty_content(self):
        v = TableValidator()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 100.0

    def test_no_tables(self):
        v = TableValidator()
        req = BlogReviewRequest(content="# Only text\n\nNo tables here.")
        result = v.validate(req)
        assert result.table_count == 0
        assert result.score == 100.0

    def test_valid_table(self):
        v = TableValidator()
        content = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.table_count == 1
        assert len(result.table_issues) == 0

    def test_invalid_table_column_mismatch(self):
        v = TableValidator()
        content = "| A | B |\n|---|---|\n| 1 | 2 | 3 |"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert len(result.table_issues) > 0

    def test_invalid_separator(self):
        v = TableValidator()
        content = "| A | B |\n| X | Y |\n| 1 | 2 |"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert len(result.table_issues) > 0

    def test_aligned_table(self):
        v = TableValidator()
        content = "| L | C | R |\n|:--|:-:|--:|\n| a | b | c |"
        req = BlogReviewRequest(content=content)
        result = v.validate(req)
        assert result.table_count == 1
        assert len(result.table_issues) == 0


class TestImageValidator:
    def test_name(self):
        v = ImageValidator()
        assert v.name() == "Image Validation"

    def test_empty_content(self):
        v = ImageValidator()
        req = BlogReviewRequest(content="")
        result = v.validate(req)
        assert result.score == 100.0

    def test_no_images(self):
        v = ImageValidator()
        req = BlogReviewRequest(content="# Just text\n\nNo images here.")
        result = v.validate(req)
        assert result.image_count == 0
        assert result.score == 100.0

    def test_valid_image(self):
        v = ImageValidator()
        req = BlogReviewRequest(content="![Python Logo](/images/python.png)")
        result = v.validate(req)
        assert result.image_count == 1
        assert result.images_missing_alt == 0

    def test_missing_alt(self):
        v = ImageValidator()
        req = BlogReviewRequest(content="![](/images/photo.png)")
        result = v.validate(req)
        assert result.images_missing_alt == 1
        assert len(result.image_issues) > 0

    def test_html_image(self):
        v = ImageValidator()
        req = BlogReviewRequest(content='<img src="/img.png" alt="Example">')
        result = v.validate(req)
        assert result.image_count == 1

    def test_http_warning(self):
        v = ImageValidator()
        req = BlogReviewRequest(content="![Image](http://example.com/img.png)")
        result = v.validate(req)
        assert len(result.image_issues) > 0
