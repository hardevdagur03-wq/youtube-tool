"""Tests for the Outline Generation Engine.

All existing tests continue to work unchanged.
"""

from __future__ import annotations

from outline_generator.outline_models import (
    ContentOutline, SectionPlan, TitleInfo, IntroPlan,
    ProblemAnalysis, TableRecommendation, ImageRecommendation,
    ExamplePlan, FAQPlan, CTAInfo, SummaryPlan,
    WordCountPlan, ReadingTimeInfo, OutlineMetadata,
)
from outline_generator.title_engine import TitleEngine
from outline_generator.intro_planner import IntroPlanner
from outline_generator.problem_importance_planner import ProblemImportancePlanner
from outline_generator.heading_generator import HeadingGenerator
from outline_generator.section_planner import SectionPlanner
from outline_generator.table_planner import TablePlanner
from outline_generator.image_planner import ImagePlanner
from outline_generator.example_engine import ExampleEngine
from outline_generator.faq_planner import FAQPlanner
from outline_generator.cta_planner import CTAPlanner
from outline_generator.summary_planner import SummaryPlanner
from outline_generator.wordcount_estimator import WordCountEstimator
from outline_generator.readability_estimator import ReadingTimeEstimator
from outline_generator.outline_validator import OutlineValidator
from outline_generator.outline_engine import OutlineEngine
from outline_generator.outline_service import OutlineService

SAMPLE_KG = {
    "entities": [
        {"name": "Python", "type": "technology", "importance_score": 1.0},
        {"name": "Pandas", "type": "library", "importance_score": 0.8},
    ],
    "facts": [
        {"statement": "Python is a high-level programming language.", "category": "definition"},
        {"statement": "Pandas is essential for data analysis.", "category": "insight"},
    ],
    "definitions": [{"term": "API", "definition": "Application Programming Interface"}],
    "pain_points": [{"problem": "Steep learning curve", "severity": "high"}],
    "statistics": [{"value": "50", "unit": "percent"}],
}

SAMPLE_SEO_PLAN = {
    "keyword_strategy": {
        "primary_keyword": "Python Programming for Data Science",
        "secondary_keywords": [
            {"keyword": "data analysis", "type": "secondary", "priority": 8},
            {"keyword": "machine learning", "type": "secondary", "priority": 7},
            {"keyword": "Pandas", "type": "semantic", "priority": 6},
        ],
    },
    "search_intent": {"primary_intent": "educational"},
    "target_audience": {"primary_audience": "Data Scientists", "pain_points": ["Complex tools"]},
    "content_strategy": {"content_depth": "comprehensive", "recommended_word_count": 2500},
    "faqs": [{"question": "What is Python?", "intent": "informational", "priority": 8}],
}

SAMPLE_ANALYSIS = {
    "primary_topic": "Python Programming for Data Science",
    "search_intent": "educational",
    "target_audience": "Data Scientists",
    "experience_level": "intermediate",
    "pain_points": ["Steep learning curve", "Data cleaning is time-consuming"],
    "key_takeaways": ["Python is popular", "Pandas is essential"],
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestOutlineModels:
    def test_default_outline(self):
        o = ContentOutline()
        assert o.title.primary_title == ""
        assert len(o.sections) == 0

    def test_title_info(self):
        t = TitleInfo(primary_title="Python Guide", seo_score=0.8)
        assert t.primary_title == "Python Guide"

    def test_section_plan(self):
        s = SectionPlan(heading="Introduction", heading_tag="h2", order=1)
        assert s.heading == "Introduction"
        assert s.target_word_count == 200

    def test_table_recommendation(self):
        t = TableRecommendation(title="Comparison Table", columns=["A", "B"])
        assert t.title == "Comparison Table"

    def test_image_recommendation(self):
        img = ImageRecommendation(type="diagram", purpose="Show concept")
        assert img.type == "diagram"

    def test_example_plan(self):
        e = ExamplePlan(type="case_study", topic="Success story")
        assert e.type == "case_study"

    def test_faq_plan(self):
        f = FAQPlan(question="What is Python?")
        assert f.question == "What is Python?"

    def test_cta_info(self):
        c = CTAInfo(type="primary", text="Subscribe now")
        assert c.text == "Subscribe now"

    def test_summary_plan(self):
        s = SummaryPlan(key_takeaways=["Learn Python"])
        assert s.key_takeaways == ["Learn Python"]

    def test_word_count_plan(self):
        w = WordCountPlan(total_target=2000)
        assert w.total_target == 2000

    def test_reading_time_info(self):
        r = ReadingTimeInfo(minutes=10, reading_level="intermediate")
        assert r.minutes == 10

    def test_outline_summary(self):
        o = ContentOutline()
        o.title.primary_title = "Python Guide"
        s = o.summary
        assert s["title"] == "Python Guide"

    def test_has_section(self):
        o = ContentOutline()
        o.sections.append(SectionPlan(heading="Intro", heading_tag="h2"))
        assert o.has_section("Intro")
        assert not o.has_section("Missing")


# ---------------------------------------------------------------------------
# Title Engine
# ---------------------------------------------------------------------------


class TestTitleEngine:
    def test_generate(self):
        engine = TitleEngine()
        info = engine.generate("Python Programming", SAMPLE_SEO_PLAN, SAMPLE_ANALYSIS)
        assert info.primary_title
        assert "Python" in info.primary_title
        assert len(info.alternative_titles) > 0

    def test_empty_keyword(self):
        engine = TitleEngine()
        info = engine.generate("", {}, SAMPLE_ANALYSIS)
        assert info.primary_title


# ---------------------------------------------------------------------------
# Intro Planner
# ---------------------------------------------------------------------------


class TestIntroPlanner:
    def test_plan(self):
        planner = IntroPlanner()
        plan = planner.plan("Python", "Data Scientists", SAMPLE_ANALYSIS, SAMPLE_SEO_PLAN)
        assert plan.hook_approach
        assert plan.reader_promise
        assert "Python" in plan.transition

    def test_empty(self):
        planner = IntroPlanner()
        plan = planner.plan("")
        assert plan.target_word_count > 0


# ---------------------------------------------------------------------------
# Problem & Importance Planner
# ---------------------------------------------------------------------------


class TestProblemImportancePlanner:
    def test_analyze(self):
        planner = ProblemImportancePlanner()
        pa = planner.analyze("Python", SAMPLE_KG, SAMPLE_SEO_PLAN, SAMPLE_ANALYSIS)
        assert pa.primary_problem
        assert len(pa.reader_pain_points) > 0

    def test_empty(self):
        planner = ProblemImportancePlanner()
        pa = planner.analyze("")
        assert pa.primary_problem


# ---------------------------------------------------------------------------
# Heading Generator
# ---------------------------------------------------------------------------


class TestHeadingGenerator:
    def test_generate(self):
        gen = HeadingGenerator()
        sections = gen.generate("Python", ["data analysis", "ML", "Pandas"], SAMPLE_KG, SAMPLE_SEO_PLAN)
        assert len(sections) > 0
        assert any("Python" in s.heading for s in sections)

    def test_all_have_goals(self):
        gen = HeadingGenerator()
        sections = gen.generate("Python", ["data analysis"])
        for s in sections:
            assert s.goal


# ---------------------------------------------------------------------------
# Section Planner
# ---------------------------------------------------------------------------


class TestSectionPlanner:
    def test_enrich(self):
        planner = SectionPlanner()
        sections = [SectionPlan(heading="Intro", heading_tag="h2", order=1)]
        enriched = planner.enrich(sections, SAMPLE_KG)
        assert len(enriched) == 1


# ---------------------------------------------------------------------------
# Table Planner
# ---------------------------------------------------------------------------


class TestTablePlanner:
    def test_recommend(self):
        planner = TablePlanner()
        tables = planner.recommend("Python", ["data analysis"], SAMPLE_SEO_PLAN)
        assert len(tables) > 0

    def test_empty(self):
        planner = TablePlanner()
        assert len(planner.recommend("Python", [])) > 0


# ---------------------------------------------------------------------------
# Image Planner
# ---------------------------------------------------------------------------


class TestImagePlanner:
    def test_recommend(self):
        planner = ImagePlanner()
        images = planner.recommend("Python", SAMPLE_SEO_PLAN)
        assert len(images) >= 2

    def test_empty(self):
        planner = ImagePlanner()
        assert len(planner.recommend("")) >= 1


# ---------------------------------------------------------------------------
# Example Engine
# ---------------------------------------------------------------------------


class TestExampleEngine:
    def test_plan(self):
        engine = ExampleEngine()
        examples = engine.plan("Python", SAMPLE_KG, SAMPLE_SEO_PLAN)
        assert len(examples) > 0

    def test_empty(self):
        engine = ExampleEngine()
        assert len(engine.plan("")) >= 1


# ---------------------------------------------------------------------------
# FAQ Planner
# ---------------------------------------------------------------------------


class TestFAQPlanner:
    def test_plan(self):
        planner = FAQPlanner()
        faqs = planner.plan("Python", SAMPLE_SEO_PLAN, SAMPLE_KG)
        assert len(faqs) > 0
        assert any("Python" in f.question for f in faqs)

    def test_empty(self):
        planner = FAQPlanner()
        assert len(planner.plan("")) > 0


# ---------------------------------------------------------------------------
# CTA Planner
# ---------------------------------------------------------------------------


class TestCTAPlanner:
    def test_plan(self):
        planner = CTAPlanner()
        ctas = planner.plan("Python")
        assert len(ctas) >= 2


# ---------------------------------------------------------------------------
# Summary Planner
# ---------------------------------------------------------------------------


class TestSummaryPlanner:
    def test_plan(self):
        planner = SummaryPlanner()
        plan = planner.plan("Python", SAMPLE_KG, SAMPLE_ANALYSIS)
        assert len(plan.key_takeaways) > 0

    def test_empty(self):
        planner = SummaryPlanner()
        assert len(planner.plan("").key_takeaways) > 0


# ---------------------------------------------------------------------------
# Word Count Estimator
# ---------------------------------------------------------------------------


class TestWordCountEstimator:
    def test_estimate(self):
        estimator = WordCountEstimator()
        sections = [SectionPlan(heading=f"H{i}", heading_tag="h2", order=i) for i in range(5)]
        plan = estimator.estimate(sections, SAMPLE_SEO_PLAN)
        assert plan.total_target > 0
        assert len(plan.section_word_counts) == 5


# ---------------------------------------------------------------------------
# Reading Time Estimator
# ---------------------------------------------------------------------------


class TestReadingTimeEstimator:
    def test_estimate(self):
        estimator = ReadingTimeEstimator()
        info = estimator.estimate(2000, SAMPLE_SEO_PLAN, SAMPLE_ANALYSIS)
        assert info.minutes > 0
        assert info.content_depth

    def test_short(self):
        estimator = ReadingTimeEstimator()
        info = estimator.estimate(300)
        assert info.reading_level == "beginner"


# ---------------------------------------------------------------------------
# Outline Validator
# ---------------------------------------------------------------------------


class TestOutlineValidator:
    def test_validate_empty(self):
        validator = OutlineValidator()
        issues = validator.validate(ContentOutline())
        assert len(issues) > 0

    def test_validate_populated(self):
        validator = OutlineValidator()
        o = ContentOutline()
        o.title.primary_title = "Python Guide"
        o.sections = [SectionPlan(heading=f"Section {i}", heading_tag="h2", goal="Goal", order=i) for i in range(5)]
        o.intro_plan.hook_approach = "Hook"
        o.ctas.append(CTAInfo(type="primary", text="Click"))
        o.faqs.append(FAQPlan(question="Q?"))
        o.word_count_plan.total_target = 2000
        issues = validator.validate(o)
        # Core validations should pass: title, sections, hook, CTAs, word count all defined
        critical_issues = [i for i in issues if "no " in i.lower() or "only " in i.lower()]
        assert len(critical_issues) <= 2  # may still flag missing intro/conclusion/FAQ sections

    def test_quality_score(self):
        validator = OutlineValidator()
        o = ContentOutline()
        o.title.primary_title = "Python Guide"
        o.sections = [SectionPlan(heading=f"H{i}", heading_tag="h2", goal="G", order=i) for i in range(6)]
        o.intro_plan.hook_approach = "Hook"
        o.problem_analysis.primary_problem = "Problem"
        o.tables.append(TableRecommendation(title="T"))
        o.images = [ImageRecommendation(type="d", purpose="p") for _ in range(2)]
        o.examples = [ExamplePlan(type="e", topic="t") for _ in range(2)]
        o.faqs = [FAQPlan(question=f"Q{i}") for i in range(3)]
        o.ctas.append(CTAInfo(type="primary", text="C"))
        o.summary_plan.key_takeaways = ["K"]
        o.word_count_plan.total_target = 2000
        o.reading_time.minutes = 5
        score = validator.compute_quality_score(o)
        assert 0 < score <= 100


# ---------------------------------------------------------------------------
# Outline Engine (Integration)
# ---------------------------------------------------------------------------


class TestOutlineEngine:
    def test_build_full(self):
        engine = OutlineEngine()
        outline = engine.build(
            knowledge_graph=SAMPLE_KG,
            seo_plan=SAMPLE_SEO_PLAN,
            analysis=SAMPLE_ANALYSIS,
            project_id="test123",
        )
        assert outline.title.primary_title
        assert len(outline.sections) > 0
        assert len(outline.tables) > 0
        assert len(outline.images) > 0
        assert len(outline.examples) > 0
        assert len(outline.faqs) > 0
        assert len(outline.ctas) > 0
        assert outline.word_count_plan.total_target > 0
        assert outline.reading_time.minutes > 0
        assert outline.metadata.quality_score > 0

    def test_build_minimal(self):
        engine = OutlineEngine()
        outline = engine.build(analysis=SAMPLE_ANALYSIS)
        assert outline.title.primary_title

    def test_build_empty(self):
        engine = OutlineEngine()
        outline = engine.build()
        assert outline.metadata.execution_time_ms >= 0
        assert isinstance(outline.sections, list)


# ---------------------------------------------------------------------------
# Outline Service
# ---------------------------------------------------------------------------


class TestOutlineService:
    def test_build_and_summary(self):
        svc = OutlineService()
        outline = svc.build(
            project_id="test123",
            knowledge_graph=SAMPLE_KG,
            seo_plan=SAMPLE_SEO_PLAN,
            analysis=SAMPLE_ANALYSIS,
        )
        summary = svc.summary(outline)
        assert summary["title"]
        assert summary["total_sections"] > 0

    def test_validate(self):
        svc = OutlineService()
        issues = svc.validate(ContentOutline())
        assert len(issues) > 0
