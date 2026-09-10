from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestPromptQuality:
    def test_prompt_clarity(self, test_prompt_templates):
        template = test_prompt_templates["blog_outline"]
        rendered = template.format(topic="Python Programming")
        assert len(rendered) > 50
        assert "Python Programming" in rendered
        assert "blog outline" in rendered.lower()

    def test_prompt_completeness(self, test_prompt_templates):
        template = test_prompt_templates["seo_analysis"]
        rendered = template.format(transcript="Sample transcript about testing.")
        required_elements = ["primary keyword", "secondary keywords", "meta title", "meta description"]
        for element in required_elements:
            assert element in rendered.lower(), f"Missing required element: {element}"

    def test_prompt_instruction_following(self, test_prompt_templates):
        template = test_prompt_templates["section_content"]
        rendered = template.format(
            heading="Python Data Types",
            word_count="500",
            context="Python has several built-in data types.",
        )
        assert "Python Data Types" in rendered
        assert "500" in rendered

    def test_prompt_has_required_sections(self, test_prompt_templates):
        template = test_prompt_templates["blog_outline"]
        rendered = template.format(topic="Machine Learning")
        required_sections = ["title", "introduction", "sections", "conclusion"]
        for section in required_sections:
            assert section in rendered.lower()

    def test_prompt_word_count_guideline(self, test_prompt_templates):
        template = test_prompt_templates["section_content"]
        rendered = template.format(
            heading="Introduction",
            word_count="300",
            context="Topic introduction.",
        )
        word_count_match = re.search(r"word count[:\s]+(\d+)", rendered, re.IGNORECASE)
        assert word_count_match is not None
        assert int(word_count_match.group(1)) == 300

    def test_prompt_structured_output_request(self, test_prompt_templates):
        template = test_prompt_templates["seo_analysis"]
        rendered = template.format(transcript="Test transcript content.")
        assert "primary keyword" in rendered.lower()
        assert ":" in rendered

    def test_prompt_no_ambiguous_instructions(self, test_prompt_templates):
        ambiguous_terms = ["maybe", "possibly", "if you want", "optional", "up to you"]
        for name, template in test_prompt_templates.items():
            rendered = template.format(
                topic="Test", transcript="Test", heading="Test",
                word_count="100", context="Test",
            )
            for term in ambiguous_terms:
                assert term not in rendered.lower(), f"Ambiguous term '{term}' found in {name}"

    def test_prompt_role_clarity(self, test_prompt_templates):
        template = test_prompt_templates["blog_outline"]
        assert "You are a professional" in template
        assert "Create" in template or "write" in template.lower()
