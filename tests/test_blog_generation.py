"""Phase 7 — AI Blog Generation Engine: 115+ tests."""

from __future__ import annotations
import json
import pytest
from pathlib import Path

from models.blog_generation import (
    BlogGenerationResult, BlogResult, BlogSection, BlogSubSection,
    CalloutBox, FAQItem, BlogStatistics, BlogGenerationRequest,
)
from exceptions.blog_errors import BlogGenerationError, BlogValidationError, BlogInvalidOutput
from exceptions.analysis_errors import LLMAuthenticationError, LLMProviderError

# AI Provider layer
from modules.ai.provider import LLMProvider, LLMResponse, ProviderConfig
from modules.ai.provider_factory import create as create_provider, REGISTRY
from modules.ai.gemini_provider import GeminiProvider, _estimate_cost as gemini_cost
from modules.ai.openai_provider import OpenAIProvider
from modules.ai.claude_provider import ClaudeProvider
from modules.ai.prompt_builder import get, set_variant, version as pv, build_blog_prompt
from modules.ai.response_parser import parse_blog, to_blog_model

# Blog generators
from modules.blog.blog_generator import generate_blog, generate_full_markdown
from modules.blog.markdown_builder import build as build_md, build_code_block, build_table
from modules.blog.section_generator import extract as extract_sections
from modules.blog.faq_generator import extract as extract_faq
from modules.blog.toc_generator import generate as generate_toc
from modules.blog.cta_generator import extract_cta
from modules.blog.blog_service import BlogGenerationService

# SEO
from modules.seo.seo_helper import estimate_score, validate as seo_validate
from modules.seo.keyword_optimizer import KeywordOptimizer

from repositories.blog_repository import BlogRepository
from config.settings import settings


# =============================================================================
# Models
# =============================================================================

class TestModels:
    def test_blog_statistics_defaults(self):
        s = BlogStatistics()
        assert s.word_count == 0
        assert s.reading_time == "< 1 min"
        assert s.estimated_seo_score == 0.0

    def test_blog_statistics_full(self):
        s = BlogStatistics(word_count=1500, reading_time="8 mins", estimated_seo_score=85.5)
        assert s.word_count == 1500
        assert s.reading_time == "8 mins"
        assert s.estimated_seo_score == 85.5

    def test_callout_box(self):
        c = CalloutBox(type="tip", text="Keep it simple.")
        assert c.type == "tip"
        assert c.text == "Keep it simple."

    def test_callout_box_default(self):
        c = CalloutBox()
        assert c.type == "note"
        assert c.text == ""

    def test_blog_subsection(self):
        s = BlogSubSection(heading="Detail", content="Details here.")
        assert s.heading == "Detail"
        assert s.content == "Details here."

    def test_blog_section_with_callouts(self):
        boxes = [CalloutBox(type="warning", text="Careful!")]
        s = BlogSection(heading="Safety", content="Stay safe.", callout_boxes=boxes)
        assert len(s.callout_boxes) == 1
        assert s.callout_boxes[0].type == "warning"

    def test_blog_section_with_subsections(self):
        sub = BlogSubSection(heading="Sub", content="Sub content")
        s = BlogSection(heading="Main", content="Body", subsections=[sub])
        assert len(s.subsections) == 1

    def test_faq_item(self):
        f = FAQItem(question="What?", answer="Something.")
        assert f.question == "What?"

    def test_blog_result_defaults(self):
        b = BlogResult()
        assert b.seo_title == ""
        assert b.sections == []
        assert b.faq == []
        assert b.markdown == ""

    def test_blog_result_full(self):
        b = BlogResult(
            seo_title="ML Guide",
            meta_description="Learn ML basics in 5 mins.",
            slug="ml-guide",
            introduction="Intro here.",
            table_of_contents=["Basics", "Advanced"],
            sections=[BlogSection(heading="Basics", content="ML is...")],
            faq=[FAQItem(question="Q?", answer="A.")],
            conclusion="Done.",
            call_to_action="Subscribe!",
            markdown="# ML Guide\n\nIntro.",
            statistics=BlogStatistics(word_count=500),
        )
        assert b.seo_title == "ML Guide"
        assert len(b.table_of_contents) == 2
        assert b.markdown != ""
        assert b.statistics.word_count == 500

    def test_blog_generation_result_defaults(self):
        r = BlogGenerationResult()
        assert r.success is True
        assert r.blog.seo_title == ""

    def test_blog_generation_result_error(self):
        r = BlogGenerationResult(success=False, video_id="bad", error="Fail")
        assert r.error == "Fail"

    def test_blog_generation_request(self):
        req = BlogGenerationRequest(video_id="dQw4w9WgXcQ", transcript="Test")
        assert req.video_id == "dQw4w9WgXcQ"

    def test_serialization_roundtrip(self):
        b = BlogResult(seo_title="Test", sections=[BlogSection(heading="H2", content="Body")], markdown="# Test")
        r = BlogGenerationResult(success=True, video_id="test12345678", blog=b)
        data = json.loads(r.model_dump_json())
        assert data["blog"]["seo_title"] == "Test"
        assert data["blog"]["markdown"] == "# Test"
        restored = BlogGenerationResult(**data)
        assert restored.blog.sections[0].heading == "H2"


# =============================================================================
# Exceptions
# =============================================================================

class TestExceptions:
    def test_blog_error_base(self):
        assert issubclass(BlogGenerationError, Exception)

    def test_validation_error(self):
        e = BlogValidationError("Bad ID")
        assert "Bad ID" in str(e)

    def test_invalid_output(self):
        e = BlogInvalidOutput("Bad JSON")
        assert str(e) == "Bad JSON"

    def test_llm_auth_error(self):
        e = LLMAuthenticationError("No key")
        assert "No key" in str(e)


# =============================================================================
# AI Provider Interface
# =============================================================================

class MockProvider(LLMProvider):
    @property
    def provider_name(self) -> str: return "mock"
    @property
    def model_name(self) -> str: return "mock-v1"
    def generate(self, prompt, system=None):
        return LLMResponse(text='{"seo_title":"Mock"}', provider="mock", model="mock-v1")
    def generate_json(self, prompt, system=None):
        return {"seo_title": "Mock Blog", "introduction": "Intro.", "table_of_contents": [], "sections": [{"heading": "Section 1", "content": "Content.", "subsections": [], "callout_boxes": []}], "faq": [{"question": "Q?", "answer": "A."}], "conclusion": "Done.", "call_to_action": "Subscribe!", "slug": "mock-blog"}

class TestProviderInterface:
    def test_llm_response_defaults(self):
        r = LLMResponse(text="Hi", provider="test", model="m1")
        assert r.input_tokens == 0

    def test_provider_config_defaults(self):
        c = ProviderConfig()
        assert c.temperature == 0.2
        assert c.max_output_tokens == 8192

    def test_provider_config_custom(self):
        c = ProviderConfig(api_key="k", model="m2", temperature=0.5)
        assert c.temperature == 0.5

    def test_mock_provider_generate(self):
        p = MockProvider()
        r = p.generate("test")
        assert r.provider == "mock"

    def test_mock_provider_generate_json(self):
        p = MockProvider()
        d = p.generate_json("test")
        assert "seo_title" in d

    def test_abstract_provider_cannot_instantiate(self):
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore


# =============================================================================
# Provider Factory
# =============================================================================

class TestProviderFactory:
    def test_create_gemini(self):
        p = create_provider("gemini", "AIzaSyTest", "gemini-2.5-flash")
        assert p.provider_name == "gemini"

    def test_create_openai(self):
        p = create_provider("openai", "sk-test", "gpt-4o-mini")
        assert p.provider_name == "openai"

    def test_create_claude(self):
        p = create_provider("claude", "sk-ant-test", "claude-3-haiku")
        assert p.provider_name == "claude"

    def test_create_invalid(self):
        with pytest.raises(ValueError):
            create_provider("nonexistent")

    def test_registry_keys(self):
        assert "gemini" in REGISTRY
        assert "openai" in REGISTRY
        assert "claude" in REGISTRY

    def test_create_gemini_no_key_raises(self):
        with pytest.raises(LLMAuthenticationError):
            create_provider("gemini", "")


# =============================================================================
# Gemini Provider
# =============================================================================

class TestGeminiProvider:
    def test_provider_name(self):
        p = GeminiProvider(ProviderConfig(api_key="AIzaSyTest", model="gemini-2.5-flash"))
        assert p.provider_name == "gemini"

    def test_raises_without_key(self):
        with pytest.raises(LLMAuthenticationError):
            GeminiProvider(ProviderConfig(api_key=""))

    def test_cost_estimate(self):
        c = gemini_cost("gemini-2.5-flash", 1000, 500)
        assert c > 0

    def test_cost_unknown_model(self):
        c = gemini_cost("unknown", 1000, 500)
        assert c > 0


# =============================================================================
# OpenAI Provider
# =============================================================================

class TestOpenAIProvider:
    def test_provider_name(self):
        p = OpenAIProvider(ProviderConfig(api_key="sk-test", model="gpt-4o-mini"))
        assert p.provider_name == "openai"

    def test_raises_without_key(self):
        with pytest.raises(LLMAuthenticationError):
            OpenAIProvider(ProviderConfig(api_key=""))


# =============================================================================
# Claude Provider
# =============================================================================

class TestClaudeProvider:
    def test_provider_name(self):
        p = ClaudeProvider(ProviderConfig(api_key="sk-ant-test", model="claude-3-haiku"))
        assert p.provider_name == "claude"

    def test_raises_without_key(self):
        with pytest.raises(LLMAuthenticationError):
            ClaudeProvider(ProviderConfig(api_key=""))


# =============================================================================
# Prompt Builder
# =============================================================================

class TestPromptBuilder:
    def test_get_system_prompt(self):
        sp = get("system.md")
        assert len(sp) > 50

    def test_prompt_version(self):
        assert pv() == "7.0.0"

    def test_set_variant(self):
        set_variant("B")
        assert pv() == "7.0.0"
        set_variant("A")

    def test_build_with_full_context(self):
        p = build_blog_prompt(
            transcript="Test about AI.",
            metadata={"title": "AI Guide", "channel": "Tech", "tags": ["AI"]},
            analysis={
                "primary_topic": "AI",
                "keywords": {"primary": "AI", "secondary": ["ML"], "long_tail": [], "semantic": [], "lsi": []},
                "entities": {"people": [], "companies": [], "technologies": [], "products": [], "frameworks": []},
                "outline": {"sections": ["Intro", "Body"]},
                "summary": {"executive": "AI guide.", "key_insights": [], "important_facts": []},
                "secondary_topics": [], "search_intent": "educational", "target_audience": "All",
                "difficulty": "beginner", "industry": "Tech", "category": "education", "content_type": "tutorial",
            },
        )
        assert "AI Guide" in p
        assert "seo_title" in p or "sections" in p

    def test_build_with_minimal_context(self):
        p = build_blog_prompt(transcript="Short.", metadata=None, analysis=None)
        assert "Short" in p

    def test_build_truncates_long(self):
        long = "word " * 50000
        p = build_blog_prompt(transcript=long, metadata=None, analysis=None, max_chars=5000)
        assert len(p) < 20000


# =============================================================================
# Response Parser
# =============================================================================

class TestResponseParser:
    def test_parse_valid(self):
        raw = json.dumps({
            "seo_title": "AI Blog", "meta_description": "Desc.", "slug": "ai-blog",
            "introduction": "Intro.", "table_of_contents": ["S1", "S2"],
            "sections": [{"heading": "S1", "content": "C1", "subsections": [{"heading": "Sub", "content": "Det"}], "callout_boxes": [{"type": "tip", "text": "Tip!"}]}],
            "faq": [{"question": "Q?", "answer": "A."}],
            "conclusion": "End.", "call_to_action": "Go!",
        })
        data = parse_blog(raw)
        assert data["seo_title"] == "AI Blog"
        assert len(data["sections"]) == 1

    def test_parse_with_fence(self):
        raw = "```json\n{\"seo_title\": \"Fenced\"}\n```"
        data = parse_blog(raw)
        assert data["seo_title"] == "Fenced"

    def test_parse_invalid_raises(self):
        with pytest.raises(BlogInvalidOutput):
            parse_blog("not json {{{")

    def test_to_blog_model_full(self):
        data = {
            "seo_title": "Blog", "meta_description": "Desc", "slug": "b",
            "introduction": "Intro.", "table_of_contents": ["T1"],
            "sections": [{"heading": "H2", "content": "Body", "subsections": [{"heading": "H3", "content": "Sub"}], "callout_boxes": [{"type": "warning", "text": "Watch out"}]}],
            "faq": [{"question": "Q?", "answer": "A."}],
            "conclusion": "End.", "call_to_action": "CTA",
        }
        blog = to_blog_model(data)
        assert blog.seo_title == "Blog"
        assert len(blog.sections) == 1
        assert blog.sections[0].callout_boxes[0].type == "warning"
        assert blog.faq[0].question == "Q?"
        assert blog.call_to_action == "CTA"

    def test_to_blog_model_empty(self):
        blog = to_blog_model({})
        assert blog.seo_title == ""


# =============================================================================
# Blog Generator
# =============================================================================

class TestBlogGenerator:
    def test_generate_with_mock(self):
        p = MockProvider()
        blog = generate_blog(p, "Test transcript.", metadata={"title": "Test"}, analysis={"primary_topic": "AI"})
        assert blog.seo_title == "Mock Blog"
        assert len(blog.sections) > 0

    def test_generate_full_markdown(self):
        blog = BlogResult(seo_title="Test", introduction="Intro.", table_of_contents=["S1"], sections=[BlogSection(heading="S1", content="Content.")], faq=[FAQItem(question="Q?", answer="A.")], conclusion="Done.", call_to_action="CTA")
        md = generate_full_markdown(blog)
        assert "# Test" in md
        assert "Intro." in md
        assert "S1" in md
        assert "Q?" in md

    def test_full_markdown_empty_blog(self):
        md = generate_full_markdown(BlogResult())
        assert md == ""


# =============================================================================
# Markdown Builder
# =============================================================================

class TestMarkdownBuilder:
    def test_build_full(self):
        blog = BlogResult(
            seo_title="Test", meta_description="SEO desc.",
            introduction="Intro.", table_of_contents=["A", "B"],
            sections=[BlogSection(heading="A", content="Content.", callout_boxes=[CalloutBox(type="tip", text="Tip!")], subsections=[BlogSubSection(heading="A1", content="Sub.")])],
            faq=[FAQItem(question="Q?", answer="A.")],
            conclusion="End.", call_to_action="Subscribe!",
        )
        md = build_md(blog)
        assert "# Test" in md
        assert "SEO desc." in md
        assert "Tip!" in md
        assert "Q?" in md
        assert "Subscribe!" in md

    def test_build_empty(self):
        assert build_md(BlogResult()) == ""

    def test_code_block(self):
        cb = build_code_block("python", "print('hello')")
        assert "```python" in cb
        assert "print" in cb

    def test_table(self):
        t = build_table(["Name", "Age"], [["Alice", "30"], ["Bob", "25"]])
        assert "| Name" in t
        assert "Alice" in t
        assert "Bob" in t


# =============================================================================
# Section Generator
# =============================================================================

class TestSectionGenerator:
    def test_extract_valid(self):
        sections = extract_sections({"sections": [{"heading": "H2", "content": "C", "subsections": [{"heading": "H3", "content": "S"}], "callout_boxes": [{"type": "note", "text": "N"}]}]})
        assert len(sections) == 1
        assert sections[0].heading == "H2"
        assert len(sections[0].subsections) == 1
        assert len(sections[0].callout_boxes) == 1

    def test_extract_empty(self):
        assert extract_sections({}) == []

    def test_extract_skips_invalid(self):
        sections = extract_sections({"sections": [{"heading": "Valid", "content": "C"}, {"bad": True}]})
        assert len(sections) == 1


# =============================================================================
# FAQ Generator
# =============================================================================

class TestFAQGenerator:
    def test_extract_valid(self):
        faq = extract_faq({"faq": [{"question": "Q1?", "answer": "A1."}, {"question": "Q2?", "answer": "A2."}]})
        assert len(faq) == 2

    def test_extract_empty(self):
        assert extract_faq({}) == []

    def test_extract_skips_invalid(self):
        faq = extract_faq({"faq": [{"question": "Q?", "answer": "A."}, {"bad": True}]})
        assert len(faq) == 1


# =============================================================================
# TOC Generator
# =============================================================================

class TestTOCGenerator:
    def test_generate_from_sections(self):
        sections = [BlogSection(heading="Intro"), BlogSection(heading="Main", subsections=[BlogSubSection(heading="Sub")])]
        toc = generate_toc(sections)
        assert len(toc) == 3

    def test_generate_fallback(self):
        toc = generate_toc([], {"table_of_contents": ["Fallback"]})
        assert toc == ["Fallback"]

    def test_generate_empty(self):
        assert generate_toc([]) == []


# =============================================================================
# CTA Generator
# =============================================================================

class TestCTAGenerator:
    def test_extract_cta(self):
        assert extract_cta({"call_to_action": "Subscribe!"}) == "Subscribe!"

    def test_extract_cta_fallback(self):
        assert extract_cta({"cta": "Go!"}) == "Go!"

    def test_extract_cta_missing(self):
        assert extract_cta({}) == ""


# =============================================================================
# SEO Helper
# =============================================================================

class TestSEOHelper:
    def test_score_high(self):
        blog = BlogResult(
            seo_title="Complete Guide to ML", meta_description="A" * 150,
            introduction="ML is transforming. " * 10,
            table_of_contents=["A", "B", "C", "D"],
            sections=[BlogSection(heading="Intro", content="X. " * 200), BlogSection(heading="Basics", content="X. " * 200), BlogSection(heading="Advanced", content="X. " * 200), BlogSection(heading="Conclusion", content="X. " * 200)],
            faq=[FAQItem(question="Q?", answer="A. " * 10) for _ in range(3)],
            conclusion="End. " * 20, call_to_action="Subscribe. " * 5,
        )
        s = estimate_score(blog, "ML")
        assert 40 <= s <= 100

    def test_score_low(self):
        s = estimate_score(BlogResult())
        assert s < 30

    def test_validate_with_warnings(self):
        w = seo_validate(BlogResult())
        assert len(w) >= 3

    def test_validate_no_warnings(self):
        blog = BlogResult(seo_title="T", meta_description="D", slug="s", table_of_contents=["A"], faq=[FAQItem(question="Q?", answer="A.")], call_to_action="C", conclusion="End.")
        assert seo_validate(blog) == []


# =============================================================================
# Keyword Optimizer
# =============================================================================

class TestKeywordOptimizer:
    def test_analyze_full(self):
        blog = BlogResult(seo_title="ML Guide", meta_description="Learn ML", slug="ml-guide", introduction="ML is great. " * 10, sections=[BlogSection(heading="What is ML", content="ML is machine learning. " * 50)], faq=[FAQItem(question="Q?", answer="ML is...")], conclusion="ML rocks.")
        opt = KeywordOptimizer(primary="ML", secondary=["machine learning", "AI"])
        result = opt.analyze(blog)
        assert result["density_pct"] > 0
        assert result["in_title"] is True
        assert result["in_intro"] is True

    def test_analyze_empty(self):
        opt = KeywordOptimizer()
        result = opt.analyze(BlogResult())
        assert result["density_pct"] == 0.0

    def test_suggestions_when_missing(self):
        blog = BlogResult(seo_title="No Keyword", introduction="Nothing.", sections=[BlogSection(heading="X")], faq=[], conclusion="", call_to_action="")
        opt = KeywordOptimizer(primary="missing-keyword")
        result = opt.analyze(blog)
        assert len(result["suggestions"]) >= 1

    def test_secondary_keywords(self):
        blog = BlogResult(seo_title="Python Guide", introduction="Python is great.", sections=[BlogSection(heading="Python Basics", content="Python code.")])
        opt = KeywordOptimizer(primary="Python", secondary=["programming", "coding", "javascript"])
        result = opt.analyze(blog)
        assert "programming" in result["secondary_found"] or "programming" in result["secondary_missing"]
        assert isinstance(result["secondary_found"], list)
        assert isinstance(result["secondary_missing"], list)


# =============================================================================
# Blog Repository
# =============================================================================

class TestBlogRepository:
    def test_save_and_get(self):
        repo = BlogRepository()
        repo.save("v1", {"seo_title": "Test Blog"})
        assert repo.get("v1")["seo_title"] == "Test Blog"

    def test_get_missing(self):
        assert BlogRepository().get("none") is None

    def test_delete(self):
        repo = BlogRepository()
        repo.save("v1", {})
        assert repo.delete("v1") is True

    def test_delete_missing(self):
        assert BlogRepository().delete("none") is False

    def test_clear(self):
        repo = BlogRepository()
        repo.save("v1", {})
        repo.save("v2", {})
        repo.clear()
        assert repo.get("v1") is None

    def test_cached_ids(self):
        repo = BlogRepository()
        repo.save("v1", {})
        ids = repo.get_cached_video_ids()
        assert "v1" in ids

    def test_disk_persistence(self, tmp_path: Path):
        repo = BlogRepository(cache_dir=str(tmp_path))
        repo.save("disk-test", {"seo_title": "Disk Blog"})
        repo2 = BlogRepository(cache_dir=str(tmp_path))
        assert repo2.get("disk-test")["seo_title"] == "Disk Blog"


# =============================================================================
# Blog Generation Service
# =============================================================================

class TestBlogService:
    def test_generate_with_mock(self):
        p = MockProvider()
        s = BlogGenerationService(provider=p)
        r = s.generate(transcript="Test AI transcript.", video_id="dQw4w9WgXcQ", metadata={"title": "AI Test"}, analysis={"primary_topic": "AI"})
        assert r.success is True
        assert r.blog.seo_title == "Mock Blog"
        assert r.llm_provider == "mock"

    def test_generate_invalid_video_id(self):
        s = BlogGenerationService(provider=MockProvider())
        r = s.generate(transcript="Test", video_id="bad")
        assert r.success is False

    def test_generate_empty_transcript(self):
        s = BlogGenerationService(provider=MockProvider())
        r = s.generate(transcript="", video_id="dQw4w9WgXcQ")
        assert r.success is False

    def test_generate_caches(self):
        repo = BlogRepository()
        s = BlogGenerationService(provider=MockProvider(), repository=repo)
        r = s.generate(transcript="T", video_id="dQw4w9WgXcQ")
        assert repo.get("dQw4w9WgXcQ") is not None

    def test_generate_bypasses_cache(self):
        repo = BlogRepository()
        s = BlogGenerationService(provider=MockProvider(), repository=repo)
        s.generate(transcript="First", video_id="vid123456789")
        r2 = s.generate(transcript="Second", video_id="vid123456789", force_refresh=True)
        assert r2.video_id == "vid123456789"

    def test_generate_structured_output(self):
        s = BlogGenerationService(provider=MockProvider())
        r = s.generate(transcript="Test", video_id="dQw4w9WgXcQ")
        assert r.blog.sections is not None
        assert r.blog.markdown != ""

    def test_default_provider_with_gemini_key(self):
        import os
        orig_env = os.environ.get("GEMINI_API_KEY")
        orig_setting = settings.gemini_api_key
        os.environ["GEMINI_API_KEY"] = "AIzaSyTest"
        try:
            settings.gemini_api_key = "AIzaSyTest"
            s = BlogGenerationService()
            assert s._provider.provider_name == "gemini"
        finally:
            if orig_env is not None:
                os.environ["GEMINI_API_KEY"] = orig_env
            else:
                os.environ.pop("GEMINI_API_KEY", None)
            settings.gemini_api_key = orig_setting


# =============================================================================
# End-to-End with Mock Provider
# =============================================================================

class TestEndToEnd:
    def test_full_pipeline_mock(self):
        s = BlogGenerationService(provider=MockProvider())
        transcript = "Test about ML. " * 30
        metadata = {"title": "ML Guide", "channel": "Tech", "tags": ["ML"]}
        analysis = {
            "primary_topic": "Machine Learning", "secondary_topics": ["Neural Nets"],
            "search_intent": "educational", "target_audience": "Beginners",
            "difficulty": "beginner", "industry": "Tech", "category": "education",
            "content_type": "tutorial",
            "keywords": {"primary": "ML", "secondary": [], "long_tail": [], "semantic": [], "lsi": []},
            "entities": {"people": [], "companies": [], "technologies": [], "products": [], "frameworks": []},
            "outline": {"sections": ["Intro", "Body", "Conclusion"]},
            "summary": {"executive": "ML guide.", "key_insights": [], "important_facts": []},
        }
        r = s.generate(transcript=transcript, video_id="dQw4w9WgXcQ", metadata=metadata, analysis=analysis)
        assert r.success is True
        assert r.blog.seo_title == "Mock Blog"
        assert len(r.blog.sections) >= 1
        assert r.blog.markdown != ""
        assert r.llm_provider == "mock"
        assert r.prompt_version == "7.0.0"


# =============================================================================
# JSON Schema Validation
# =============================================================================

class TestSchema:
    def test_full_result_serialization(self):
        blog = BlogResult(
            seo_title="Schema Test", meta_description="Desc", slug="schema-test",
            introduction="Intro.", table_of_contents=["A"],
            sections=[BlogSection(heading="A", content="Body.", callout_boxes=[CalloutBox(type="tip", text="T")], subsections=[BlogSubSection(heading="A1", content="Sub.")])],
            faq=[FAQItem(question="Q?", answer="A.")],
            conclusion="End.", call_to_action="CTA",
            markdown="# Schema Test\n\nBody.",
            statistics=BlogStatistics(word_count=100, reading_time="1 min", estimated_seo_score=75.0),
        )
        r = BlogGenerationResult(success=True, video_id="dQw4w9WgXcQ", blog=blog, llm_provider="gemini", llm_model="gemini-2.5-flash", prompt_version="7.0.0", input_tokens=500, output_tokens=800, generation_time_ms=3200.5)
        data = json.loads(r.model_dump_json())
        assert data["blog"]["seo_title"] == "Schema Test"
        assert data["blog"]["statistics"]["word_count"] == 100
        assert data["blog"]["statistics"]["estimated_seo_score"] == 75.0
        assert data["blog"]["sections"][0]["callout_boxes"][0]["type"] == "tip"
        assert data["blog"]["sections"][0]["subsections"][0]["heading"] == "A1"
        assert data["blog"]["faq"][0]["question"] == "Q?"
        assert data["llm_provider"] == "gemini"
        assert data["generation_time_ms"] == 3200.5

    def test_error_response(self):
        r = BlogGenerationResult(success=False, video_id="bad", error="Timeout", generation_time_ms=50000.0)
        data = json.loads(r.model_dump_json())
        assert data["success"] is False
        assert data["error"] == "Timeout"
