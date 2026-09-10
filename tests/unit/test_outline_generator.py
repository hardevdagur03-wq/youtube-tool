from __future__ import annotations

import pytest

SAMPLE_KG = {
    "entities": [
        {"name": "Python", "type": "technology", "importance_score": 1.0},
        {"name": "Pandas", "type": "library", "importance_score": 0.8},
    ],
    "facts": [{"statement": "Python is a high-level programming language.", "category": "definition"}],
    "definitions": [{"term": "API", "definition": "Application Programming Interface"}],
    "pain_points": [{"problem": "Steep learning curve", "severity": "high"}],
}

SAMPLE_SEO_PLAN = {
    "keyword_strategy": {
        "primary_keyword": "Python Programming for Data Science",
        "secondary_keywords": [{"keyword": "data analysis", "type": "secondary"}],
    },
    "search_intent": {"primary_intent": "educational"},
    "target_audience": {"primary_audience": "Data Scientists"},
    "content_strategy": {"content_depth": "comprehensive", "recommended_word_count": 2500},
}

SAMPLE_ANALYSIS = {
    "primary_topic": "Python Programming for Data Science",
    "search_intent": "educational",
    "target_audience": "Data Scientists",
    "experience_level": "intermediate",
    "pain_points": ["Steep learning curve", "Data cleaning is time-consuming"],
    "key_takeaways": ["Python is popular", "Pandas is essential"],
}


class TestOutlineModels:
    def test_default_outline(self):
        from outline_generator.outline_models import ContentOutline
        o = ContentOutline()
        assert o.title.primary_title == ""
        assert len(o.sections) == 0

    def test_title_info(self):
        from outline_generator.outline_models import TitleInfo
        t = TitleInfo(primary_title="Python Guide", seo_score=0.8)
        assert t.primary_title == "Python Guide"

    def test_section_plan(self):
        from outline_generator.outline_models import SectionPlan
        s = SectionPlan(heading="Introduction", heading_tag="h2", order=1)
        assert s.heading == "Introduction"
        assert s.target_word_count == 200


class TestTitleEngine:
    def test_generate(self):
        from outline_generator.title_engine import TitleEngine
        engine = TitleEngine()
        info = engine.generate("Python Programming", SAMPLE_SEO_PLAN, SAMPLE_ANALYSIS)
        assert info.primary_title
        assert "Python" in info.primary_title
        assert len(info.alternative_titles) > 0

    def test_generate_empty(self):
        from outline_generator.title_engine import TitleEngine
        engine = TitleEngine()
        info = engine.generate("", {}, SAMPLE_ANALYSIS)
        assert info.primary_title


class TestIntroPlanner:
    def test_plan(self):
        from outline_generator.intro_planner import IntroPlanner
        planner = IntroPlanner()
        plan = planner.plan("Python", "Data Scientists", SAMPLE_ANALYSIS, SAMPLE_SEO_PLAN)
        assert plan.hook_approach
        assert plan.reader_promise

    def test_plan_empty(self):
        from outline_generator.intro_planner import IntroPlanner
        planner = IntroPlanner()
        plan = planner.plan("")
        assert plan.target_word_count > 0


class TestProblemImportancePlanner:
    def test_analyze(self):
        from outline_generator.problem_importance_planner import ProblemImportancePlanner
        planner = ProblemImportancePlanner()
        pa = planner.analyze("Python", SAMPLE_KG, SAMPLE_SEO_PLAN, SAMPLE_ANALYSIS)
        assert pa.primary_problem
        assert len(pa.reader_pain_points) > 0

    def test_analyze_empty(self):
        from outline_generator.problem_importance_planner import ProblemImportancePlanner
        planner = ProblemImportancePlanner()
        pa = planner.analyze("")
        assert pa.primary_problem


class TestHeadingGenerator:
    def test_generate(self):
        from outline_generator.heading_generator import HeadingGenerator
        gen = HeadingGenerator()
        sections = gen.generate("Python", ["data analysis", "ML"], SAMPLE_KG, SAMPLE_SEO_PLAN)
        assert len(sections) > 0
        assert any("Python" in s.heading for s in sections)

    def test_all_have_goals(self):
        from outline_generator.heading_generator import HeadingGenerator
        gen = HeadingGenerator()
        sections = gen.generate("Python", ["data analysis"])
        for s in sections:
            assert s.goal


class TestSectionPlanner:
    def test_enrich(self):
        from outline_generator.section_planner import SectionPlanner
        from outline_generator.outline_models import SectionPlan
        planner = SectionPlanner()
        sections = [SectionPlan(heading="Intro", heading_tag="h2", order=1)]
        enriched = planner.enrich(sections, SAMPLE_KG)
        assert len(enriched) == 1


class TestTablePlanner:
    def test_recommend(self):
        from outline_generator.table_planner import TablePlanner
        planner = TablePlanner()
        tables = planner.recommend("Python", ["data analysis"], SAMPLE_SEO_PLAN)
        assert len(tables) > 0


class TestImagePlanner:
    def test_recommend(self):
        from outline_generator.image_planner import ImagePlanner
        planner = ImagePlanner()
        images = planner.recommend("Python", SAMPLE_SEO_PLAN)
        assert len(images) >= 2


class TestExampleEngine:
    def test_plan(self):
        from outline_generator.example_engine import ExampleEngine
        engine = ExampleEngine()
        examples = engine.plan("Python", SAMPLE_KG, SAMPLE_SEO_PLAN)
        assert len(examples) > 0


class TestFAQPlanner:
    def test_plan(self):
        from outline_generator.faq_planner import FAQPlanner
        planner = FAQPlanner()
        faqs = planner.plan("Python", SAMPLE_SEO_PLAN, SAMPLE_KG)
        assert len(faqs) > 0
        assert any("Python" in f.question for f in faqs)


class TestCTAPlanner:
    def test_plan(self):
        from outline_generator.cta_planner import CTAPlanner
        planner = CTAPlanner()
        ctas = planner.plan("Python")
        assert len(ctas) >= 2


class TestSummaryPlanner:
    def test_plan(self):
        from outline_generator.summary_planner import SummaryPlanner
        planner = SummaryPlanner()
        plan = planner.plan("Python", SAMPLE_KG, SAMPLE_ANALYSIS)
        assert len(plan.key_takeaways) > 0


class TestWordCountEstimator:
    def test_estimate(self):
        from outline_generator.wordcount_estimator import WordCountEstimator
        from outline_generator.outline_models import SectionPlan
        estimator = WordCountEstimator()
        sections = [SectionPlan(heading=f"H{i}", heading_tag="h2", order=i) for i in range(5)]
        plan = estimator.estimate(sections, SAMPLE_SEO_PLAN)
        assert plan.total_target > 0
        assert len(plan.section_word_counts) == 5


class TestReadingTimeEstimator:
    def test_estimate(self):
        from outline_generator.readability_estimator import ReadingTimeEstimator
        estimator = ReadingTimeEstimator()
        info = estimator.estimate(2000, SAMPLE_SEO_PLAN, SAMPLE_ANALYSIS)
        assert info.minutes > 0
        assert info.content_depth

    def test_estimate_short(self):
        from outline_generator.readability_estimator import ReadingTimeEstimator
        estimator = ReadingTimeEstimator()
        info = estimator.estimate(300)
        assert info.reading_level == "beginner"


class TestOutlineValidator:
    def test_validate_empty(self):
        from outline_generator.outline_validator import OutlineValidator
        from outline_generator.outline_models import ContentOutline
        validator = OutlineValidator()
        issues = validator.validate(ContentOutline())
        assert len(issues) > 0

    def test_validate_populated(self):
        from outline_generator.outline_validator import OutlineValidator
        from outline_generator.outline_models import ContentOutline, SectionPlan, CTAInfo, FAQPlan, TableRecommendation, ImageRecommendation, ExamplePlan
        validator = OutlineValidator()
        o = ContentOutline()
        o.title.primary_title = "Python Guide"
        o.sections = [SectionPlan(heading=f"Section {i}", heading_tag="h2", goal="Goal", order=i) for i in range(5)]
        o.intro_plan.hook_approach = "Hook"
        o.ctas.append(CTAInfo(type="primary", text="Click"))
        o.faqs.append(FAQPlan(question="Q?"))
        o.word_count_plan.total_target = 2000
        issues = validator.validate(o)
        critical = [i for i in issues if "no " in i.lower()]
        assert len(critical) <= 2

    def test_quality_score(self):
        from outline_generator.outline_validator import OutlineValidator
        from outline_generator.outline_models import ContentOutline, SectionPlan, CTAInfo, FAQPlan, TableRecommendation, ImageRecommendation, ExamplePlan
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


class TestOutlineEngine:
    def test_build_full(self):
        from outline_generator.outline_engine import OutlineEngine
        engine = OutlineEngine()
        outline = engine.build(knowledge_graph=SAMPLE_KG, seo_plan=SAMPLE_SEO_PLAN, analysis=SAMPLE_ANALYSIS, project_id="test123")
        assert outline.title.primary_title
        assert len(outline.sections) > 0
        assert outline.word_count_plan.total_target > 0
        assert outline.reading_time.minutes > 0

    def test_build_minimal(self):
        from outline_generator.outline_engine import OutlineEngine
        engine = OutlineEngine()
        outline = engine.build(analysis=SAMPLE_ANALYSIS)
        assert outline.title.primary_title

    def test_build_empty(self):
        from outline_generator.outline_engine import OutlineEngine
        engine = OutlineEngine()
        outline = engine.build()
        assert outline.metadata.execution_time_ms >= 0


class TestOutlineService:
    def test_build_and_summary(self):
        from outline_generator.outline_service import OutlineService
        svc = OutlineService()
        outline = svc.build(project_id="test123", knowledge_graph=SAMPLE_KG, seo_plan=SAMPLE_SEO_PLAN, analysis=SAMPLE_ANALYSIS)
        summary = svc.summary(outline)
        assert summary["title"]
        assert summary["total_sections"] > 0

    def test_validate(self):
        from outline_generator.outline_service import OutlineService
        from outline_generator.outline_models import ContentOutline
        svc = OutlineService()
        issues = svc.validate(ContentOutline())
        assert len(issues) > 0
