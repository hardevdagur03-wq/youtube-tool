"""Tests for Phase 9 review models."""

from __future__ import annotations
import pytest
from models.blog_review import (
    IssueSeverity, HallucinationRisk, PublishDecision, ReviewIssue,
    GrammarResult, ReadabilityResult, SEOResult, DuplicateResult,
    HeadingResult, CompletenessResult, HallucinationResult,
    FactConsistencyResult, EEATResult, LinkingResult,
    AccessibilityResult, ContentQualityResult, AIDetectionResult,
    CategoryScore, Scorecard, QualityReport, BlogReviewRequest,
    BlogReviewResponse,
)


class TestEnums:
    def test_issue_severity_values(self):
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.LOW.value == "low"

    def test_hallucination_risk_values(self):
        assert HallucinationRisk.LOW.value == "low"
        assert HallucinationRisk.MEDIUM.value == "medium"
        assert HallucinationRisk.HIGH.value == "high"

    def test_publish_decision_values(self):
        assert PublishDecision.ENTERPRISE_READY.value == "enterprise_ready"
        assert PublishDecision.PUBLISH_READY.value == "publish_ready"
        assert PublishDecision.MINOR_REVISIONS.value == "minor_revisions"
        assert PublishDecision.MAJOR_REVISIONS.value == "major_revisions"
        assert PublishDecision.REJECT.value == "reject"


class TestReviewIssue:
    def test_create_issue(self):
        issue = ReviewIssue(
            description="Test issue",
            location="Section 1",
            severity=IssueSeverity.HIGH,
            why_it_matters="It matters",
            recommended_fix="Fix it",
        )
        assert issue.description == "Test issue"
        assert issue.severity == IssueSeverity.HIGH


class TestGrammarResult:
    def test_defaults(self):
        g = GrammarResult()
        assert g.score == 100.0
        assert g.issues == []
        assert g.spelling_errors == 0

    def test_with_issues(self):
        g = GrammarResult(
            score=75.0,
            spelling_errors=3,
            grammar_errors=2,
            passive_voice_sentences=5,
        )
        assert g.score == 75.0
        assert g.spelling_errors == 3


class TestReadabilityResult:
    def test_defaults(self):
        r = ReadabilityResult()
        assert r.score == 100.0
        assert r.flesch_reading_ease == 0.0

    def test_with_values(self):
        r = ReadabilityResult(
            score=85.0,
            flesch_reading_ease=65.0,
            flesch_kincaid_grade=8.5,
            difficulty_level="Standard",
            reading_time_minutes=5.0,
        )
        assert r.score == 85.0
        assert r.difficulty_level == "Standard"


class TestSEOResult:
    def test_defaults(self):
        s = SEOResult()
        assert s.score == 100.0
        assert s.missing_elements == []

    def test_keyword_presence(self):
        s = SEOResult(
            score=70.0,
            primary_keyword_in_title=True,
            primary_keyword_in_meta_description=False,
            missing_elements=["Missing in meta description"],
        )
        assert s.primary_keyword_in_title is True
        assert s.primary_keyword_in_meta_description is False


class TestHallucinationResult:
    def test_default_risk(self):
        h = HallucinationResult()
        assert h.risk_level == HallucinationRisk.LOW
        assert h.score == 100.0

    def test_high_risk(self):
        h = HallucinationResult(
            score=40.0,
            risk_level=HallucinationRisk.HIGH,
            unsupported_claims=5,
            fabricated_references=2,
        )
        assert h.risk_level == HallucinationRisk.HIGH
        assert h.unsupported_claims == 5


class TestEEATResult:
    def test_defaults(self):
        e = EEATResult()
        assert e.score == 100.0
        assert e.experience_score == 0.0

    def test_with_scores(self):
        e = EEATResult(
            score=75.0,
            experience_score=80.0,
            expertise_score=70.0,
            authoritativeness_score=65.0,
            trustworthiness_score=85.0,
        )
        assert e.experience_score == 80.0


class TestScorecard:
    def test_create(self):
        categories = [
            CategoryScore(category="Grammar", score=90.0, weight=0.15, status="good"),
            CategoryScore(category="SEO", score=75.0, weight=0.20, status="fair"),
        ]
        sc = Scorecard(categories=categories, overall_score=82.5)
        assert len(sc.categories) == 2
        assert sc.overall_score == 82.5


class TestQualityReport:
    def test_defaults(self):
        r = QualityReport()
        assert r.overall_score == 0.0
        assert r.publish_decision == PublishDecision.REJECT
        assert r.word_count == 0

    def test_with_data(self):
        r = QualityReport(
            blog_title="Test Blog",
            word_count=1000,
            overall_score=85.0,
            publish_decision=PublishDecision.MINOR_REVISIONS,
        )
        assert r.blog_title == "Test Blog"
        assert r.overall_score == 85.0


class TestBlogReviewRequest:
    def test_create_minimal(self):
        req = BlogReviewRequest(content="Hello world")
        assert req.content == "Hello world"
        assert req.blog_title == ""

    def test_create_full(self):
        req = BlogReviewRequest(
            blog_title="Test Blog",
            primary_keyword="testing",
            secondary_keywords=["test", "qa"],
            target_audience="developers",
            content="Full blog content here",
            faq=[{"question": "What?", "answer": "This."}],
        )
        assert req.blog_title == "Test Blog"
        assert len(req.faq) == 1


class TestBlogReviewResponse:
    def test_error_response(self):
        resp = BlogReviewResponse(success=False, error="Something broke")
        assert resp.success is False
        assert resp.error == "Something broke"
        assert resp.report is None

    def test_success_response(self):
        report = QualityReport(overall_score=95.0)
        resp = BlogReviewResponse(success=True, report=report)
        assert resp.success is True
        assert resp.report.overall_score == 95.0
