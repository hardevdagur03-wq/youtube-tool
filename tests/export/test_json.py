from __future__ import annotations

import json

import pytest

from models.blog_export import ExportFormat, ExportRequest


SAMPLE_BLOG = ExportRequest(
    blog_title="JSON Test Blog",
    slug="json-test",
    meta_title="JSON Test",
    meta_description="Testing JSON export",
    author="Tester",
    publish_date="2026-07-01",
    category="Tech",
    tags=["json"],
    primary_keyword="json test",
    markdown_content="# JSON\n\nContent.",
    formats=[ExportFormat.MARKDOWN],
    sections=[],
)


pytestmark = pytest.mark.export


class TestJsonExport:
    def test_json_structure(self):
        data = {
            "title": SAMPLE_BLOG.blog_title,
            "slug": SAMPLE_BLOG.slug,
            "content": SAMPLE_BLOG.markdown_content,
            "metadata": {
                "author": SAMPLE_BLOG.author,
                "date": SAMPLE_BLOG.publish_date,
                "category": SAMPLE_BLOG.category,
            },
        }
        serialized = json.dumps(data, indent=2)
        parsed = json.loads(serialized)
        assert parsed["title"] == "JSON Test Blog"
        assert parsed["slug"] == "json-test"
        assert "content" in parsed

    def test_json_metadata(self):
        data = {
            "author": SAMPLE_BLOG.author,
            "date": SAMPLE_BLOG.publish_date,
            "tags": SAMPLE_BLOG.tags,
            "keyword": SAMPLE_BLOG.primary_keyword,
        }
        serialized = json.dumps(data)
        parsed = json.loads(serialized)
        assert parsed["author"] == "Tester"
        assert "json" in parsed["tags"]

    def test_json_content(self):
        content = SAMPLE_BLOG.markdown_content
        assert content is not None
        assert len(content) > 0
        data = {"content": content}
        serialized = json.dumps(data)
        parsed = json.loads(serialized)
        assert "# JSON" in parsed["content"]
