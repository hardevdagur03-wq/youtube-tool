"""Recommendation Engine — generates prioritized, categorized, actionable recommendations."""

from __future__ import annotations
from models.blog_review import QualityReport
from review.review_models_ext import ReviewReport, RecommendationEntry


PRIORITY_ORDER = {"must_fix": 0, "should_improve": 1, "nice_to_have": 2}


class RecommendationEngine:
    """Generates prioritized, categorized recommendations from validation results."""

    def generate(self, report: QualityReport) -> list[RecommendationEntry]:
        recommendations: list[RecommendationEntry] = []

        # Grammar recommendations
        if hasattr(report.grammar, 'score'):
            gs = report.grammar.score
            if gs < 70:
                recommendations.append(RecommendationEntry(
                    priority="must_fix",
                    category="grammar",
                    description=f"Grammar score is {gs:.0f}/100 — review and correct spelling, punctuation, and sentence structure errors",
                    impact="Critical for professionalism and reader trust",
                    effort="Medium",
                ))
            elif gs < 85:
                recommendations.append(RecommendationEntry(
                    priority="should_improve",
                    category="grammar",
                    description=f"Grammar score is {gs:.0f}/100 — minor proofreading pass recommended",
                    impact="Improves content polish",
                    effort="Low",
                ))

        # SEO recommendations
        if hasattr(report.seo, 'score'):
            ss = report.seo.score
            if ss < 60:
                recommendations.append(RecommendationEntry(
                    priority="must_fix",
                    category="seo",
                    description=f"SEO score is {ss:.0f}/100 — address missing elements: {', '.join(getattr(report.seo, 'missing_elements', [])[:3])}",
                    impact="Directly affects search engine ranking",
                    effort="Medium",
                ))
            elif ss < 80:
                recommendations.append(RecommendationEntry(
                    priority="should_improve",
                    category="seo",
                    description=f"SEO score is {ss:.0f}/100 — optimize keyword placement and meta data",
                    impact="Improves search visibility",
                    effort="Low",
                ))

        # Keyword stuffing
        if hasattr(report.seo, 'keyword_stuffing_detected') and report.seo.keyword_stuffing_detected:
            recommendations.append(RecommendationEntry(
                priority="must_fix",
                category="seo",
                description="Keyword stuffing detected — reduce keyword density to avoid SEO penalties",
                impact="Prevents search engine demotion",
                effort="Low",
            ))

        # Readability recommendations
        if hasattr(report.readability, 'score'):
            rs = report.readability.score
            if rs < 60:
                recommendations.append(RecommendationEntry(
                    priority="should_improve",
                    category="readability",
                    description=f"Readability score is {rs:.0f}/100 — simplify language, reduce sentence length, improve flow",
                    impact="Affects reader engagement and retention",
                    effort="Medium",
                ))
            elif rs < 80:
                recommendations.append(RecommendationEntry(
                    priority="nice_to_have",
                    category="readability",
                    description=f"Readability score is {rs:.0f}/100 — consider minor improvements to sentence variety",
                    impact="Enhances reading experience",
                    effort="Low",
                ))

        # Structure recommendations
        if hasattr(report.headings, 'score') and report.headings.score < 70:
            recommendations.append(RecommendationEntry(
                priority="must_fix",
                category="structure",
                description=f"Heading structure score is {report.headings.score:.0f}/100 — fix hierarchy issues",
                impact="Critical for navigation and SEO",
                effort="Low",
            ))

        if hasattr(report.duplicate, 'score') and report.duplicate.score < 80:
            recommendations.append(RecommendationEntry(
                priority="should_improve",
                category="structure",
                description="Duplicate content detected — merge or rewrite repeated sections",
                impact="Improves content uniqueness and value",
                effort="Medium",
            ))

        if hasattr(report.completeness, 'score') and report.completeness.score < 70:
            recommendations.append(RecommendationEntry(
                priority="should_improve",
                category="completeness",
                description=f"Content completeness score is {report.completeness.score:.0f}/100 — add missing sections: {', '.join(getattr(report.completeness, 'missing_sections', [])[:4])}",
                impact="Ensures comprehensive coverage of the topic",
                effort="Medium",
            ))

        # Hallucination risk recommendations
        if hasattr(report.hallucination, 'risk_level'):
            risk = report.hallucination.risk_level
            if hasattr(risk, 'value'):
                risk = risk.value
            if risk == "high":
                recommendations.append(RecommendationEntry(
                    priority="must_fix",
                    category="hallucination_risk",
                    description="High hallucination risk detected — review all flagged statements and add citations",
                    impact="Critical for factual accuracy and credibility",
                    effort="High",
                ))
            elif risk == "medium":
                recommendations.append(RecommendationEntry(
                    priority="should_improve",
                    category="hallucination_risk",
                    description="Medium hallucination risk — review flagged statements and add supporting evidence",
                    impact="Improves factual reliability",
                    effort="Medium",
                ))

        # EEAT recommendations
        if hasattr(report.eeat, 'score') and report.eeat.score < 60:
            recommendations.append(RecommendationEntry(
                priority="must_fix",
                category="eeat",
                description=f"EEAT score is {report.eeat.score:.0f}/100 — add expertise signals, author credentials, and authoritative references",
                impact="Critical for Google's quality rater guidelines",
                effort="High",
            ))

        # AI detection recommendations
        if hasattr(report.ai_detection, 'risk_level'):
            ai_risk = report.ai_detection.risk_level
            if ai_risk == "high":
                recommendations.append(RecommendationEntry(
                    priority="should_improve",
                    category="ai_detection",
                    description="High AI detection risk — revise content to sound more natural and human-written",
                    impact="Affects reader trust and perceived authenticity",
                    effort="Medium",
                ))
            elif ai_risk == "medium":
                recommendations.append(RecommendationEntry(
                    priority="nice_to_have",
                    category="ai_detection",
                    description="Medium AI detection risk — vary sentence structure and vocabulary",
                    impact="Improves natural writing feel",
                    effort="Low",
                ))

        # Accessibility recommendations
        if hasattr(report.accessibility, 'score') and report.accessibility.score < 70:
            recommendations.append(RecommendationEntry(
                priority="should_improve",
                category="accessibility",
                description=f"Accessibility score is {report.accessibility.score:.0f}/100 — add ALT text to images, improve link text",
                impact="Essential for inclusive content and SEO",
                effort="Low",
            ))

        # Internal linking recommendations
        if hasattr(report.internal_linking, 'score') and report.internal_linking.score < 70:
            recommendations.append(RecommendationEntry(
                priority="should_improve",
                category="linking",
                description="Internal linking score low — add contextual internal links to related content",
                impact="Improves site navigation and SEO authority",
                effort="Low",
            ))

        # Sort by priority
        recommendations.sort(key=lambda r: PRIORITY_ORDER.get(r.priority, 99))

        return recommendations
