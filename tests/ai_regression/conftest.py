from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class SemanticSimilarityCalculator:
    def __init__(self):
        self.keywords_sets = {}

    def jaccard_similarity(self, text1: str, text2: str) -> float:
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union)

    def entity_overlap(self, entities1: list[dict], entities2: list[dict]) -> float:
        names1 = {e["name"].lower() for e in entities1 if "name" in e}
        names2 = {e["name"].lower() for e in entities2 if "name" in e}
        if not names1 or not names2:
            return 0.0
        overlap = names1 & names2
        return len(overlap) / max(len(names1), len(names2))

    def keyword_overlap(self, kws1: list[str], kws2: list[str]) -> float:
        s1, s2 = set(k.lower() for k in kws1), set(k.lower() for k in kws2)
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / max(len(s1), len(s2))


@pytest.fixture
def similarity_calculator():
    return SemanticSimilarityCalculator()


@pytest.fixture
def mock_llm_provider():
    provider = MagicMock()
    provider.generate = AsyncMock(return_value={
        "text": (
            "Python is a versatile programming language used in data science, "
            "web development, and automation. It was created by Guido van Rossum "
            "and has become one of the most popular languages worldwide."
        ),
        "usage": {"total_tokens": 50, "prompt_tokens": 30, "completion_tokens": 20},
    })
    provider.generate_structured = AsyncMock(return_value={
        "title": "Python Programming Guide",
        "sections": [
            {"heading": "Introduction", "content": "Python overview"},
            {"heading": "Getting Started", "content": "Installation guide"},
            {"heading": "Advanced Topics", "content": "Deep dive into features"},
        ],
        "keywords": ["Python", "programming", "data science"],
        "entities": [
            {"name": "Python", "type": "language"},
            {"name": "Guido van Rossum", "type": "person"},
        ],
        "score": 85.0,
    })
    return provider


@pytest.fixture
def test_prompt_templates():
    return {
        "blog_outline": (
            "You are a professional blog writer. Create a detailed blog outline "
            "for the topic '{topic}'. Include: title, introduction, at least 5 sections, "
            "and a conclusion. Each section should have a heading and brief description."
        ),
        "seo_analysis": (
            "Analyze the following transcript for SEO opportunities. "
            "Extract: primary keyword (1), secondary keywords (3-5), "
            "meta title (max 60 chars), meta description (max 160 chars). "
            "Transcript: {transcript}"
        ),
        "section_content": (
            "Write a detailed blog section for heading '{heading}'. "
            "Target word count: {word_count}. Include relevant examples and explanations. "
            "Use the following context: {context}"
        ),
    }


@pytest.fixture
def golden_responses():
    return {
        "blog_outline": {
            "title": "Complete Python Programming Guide",
            "sections": [
                "Introduction to Python",
                "Setting Up Development Environment",
                "Python Syntax and Basics",
                "Data Structures and Algorithms",
                "Object-Oriented Programming",
                "Working with Libraries",
                "Conclusion and Next Steps",
            ],
        },
        "seo_analysis": {
            "primary_keyword": "python programming",
            "secondary_keywords": ["python tutorial", "learn python", "python for beginners"],
            "meta_title": "Complete Python Programming Guide for Beginners",
            "meta_description": "A comprehensive Python programming guide covering basics to advanced topics for beginners and experienced developers.",
        },
    }


@pytest.fixture
def sample_transcript():
    return (
        "Today we are going to learn about Python programming. "
        "Python is a high-level, interpreted programming language. "
        "It was created by Guido van Rossum and first released in 1991. "
        "Python emphasizes code readability and simplicity. "
        "It is widely used in data science, machine learning, web development, and automation. "
        "Some key features include dynamic typing, garbage collection, and extensive standard library. "
        "Popular frameworks include Django for web and TensorFlow for machine learning. "
        "Python has a large and active community with thousands of packages available."
    )
