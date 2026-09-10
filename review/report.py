"""Quality Report Generator — Phase 9.

Produces structured Markdown reports from QualityReport data.
"""

from __future__ import annotations
from models.blog_review import (
    QualityReport, Scorecard, CategoryScore, PublishDecision,
    ReviewIssue, IssueSeverity,
)


class ReportGenerator:
    """Generates human-readable Markdown quality reports."""

    def generate(self, report: QualityReport) -> str:
        lines: list[str] = []
        lines.append(f"# AI Blog Quality Report\n")
        lines.append(f"**Generated:** {report.generated_at}")
        if report.execution_time_ms:
            lines.append(f"**Analysis Time:** {report.execution_time_ms:.0f}ms")
        lines.append("")

        lines.append(self._section("Executive Summary", self._executive_summary(report)))
        lines.append(self._section("Scorecard", self._scorecard(report.scorecard)))
        lines.append(self._section("Detailed Results", self._detailed_results(report)))
        lines.append(self._section("Issues Found", self._issues_section(report)))
        lines.append(self._section("Recommendations", self._recommendations(report)))
        lines.append(self._section("Final Decision", self._decision(report)))

        return "\n".join(lines)

    def _section(self, title: str, content: str) -> str:
        return f"## {title}\n\n{content}\n\n---\n"

    def _executive_summary(self, report: QualityReport) -> str:
        return report.executive_summary or "No summary available."

    def _scorecard(self, scorecard: Scorecard) -> str:
        lines = ["| Category | Score | Status |", "|----------|------:|--------|"]
        for cat in scorecard.categories:
            emoji = self._status_emoji(cat.status)
            lines.append(f"| {emoji} {cat.category} | **{cat.score:.0f}**/100 | {cat.status.title()} |")

        lines.append("")
        lines.append(f"| **Overall** | **{scorecard.overall_score:.0f}/100** | |")
        return "\n".join(lines)

    def _detailed_results(self, report: QualityReport) -> str:
        parts: list[str] = []

        # Grammar
        if hasattr(report.grammar, 'score'):
            g = report.grammar
            parts.append(self._result_block("Grammar", g.score, [
                f"**Spelling Errors:** {g.spelling_errors}",
                f"**Grammar Errors:** {g.grammar_errors}",
                f"**Punctuation Issues:** {g.punctuation_errors}",
                f"**Passive Voice Sentences:** {g.passive_voice_sentences}",
                f"**Run-on Sentences:** {g.run_on_sentences}",
                f"**Sentence Fragments:** {g.sentence_fragments}",
            ]))

        # Readability
        if hasattr(report.readability, 'score'):
            r = report.readability
            parts.append(self._result_block("Readability", r.score, [
                f"**Flesch Reading Ease:** {r.flesch_reading_ease:.1f} ({r.difficulty_level})",
                f"**Flesch-Kincaid Grade:** {r.flesch_kincaid_grade:.1f}",
                f"**Avg Sentence Length:** {r.avg_sentence_length:.1f} words",
                f"**Avg Paragraph Length:** {r.avg_paragraph_length:.1f} sentences",
                f"**Complex Sentence Ratio:** {r.complex_sentence_ratio:.0%}",
                f"**Passive Voice:** {r.passive_voice_percentage:.0f}%",
                f"**Reading Time:** {r.reading_time_minutes:.0f} min",
                "",
                "**Improvement Suggestions:**",
            ] + [f"- {s}" for s in r.improvement_suggestions]))

        # SEO
        if hasattr(report.seo, 'score'):
            s = report.seo
            lines = [f"**Title Length:** {s.title_length} chars",
                     f"**Meta Title:** {s.meta_title_length} chars {'✓' if 30 <= s.meta_title_length <= 60 else '⚠'}",
                     f"**Meta Description:** {s.meta_description_length} chars {'✓' if 120 <= s.meta_description_length <= 160 else '⚠'}",
                     f"**Keyword in Title:** {'✓' if s.primary_keyword_in_title else '✗'}",
                     f"**Keyword in H1:** {'✓' if s.primary_keyword_in_h1 else '✗'}",
                     f"**Keyword in H2:** {'✓' if s.primary_keyword_in_h2 else '✗'}",
                     f"**Keyword in Introduction:** {'✓' if s.primary_keyword_in_introduction else '✗'}",
                     f"**Keyword in Conclusion:** {'✓' if s.primary_keyword_in_conclusion else '✗'}",
                     ""]
            if s.keyword_stuffing_detected:
                lines.append("⚠ **Keyword stuffing detected**")
                lines.append("")
            if s.missing_elements:
                lines.append("**Missing Elements:**")
                lines.extend(f"- {e}" for e in s.missing_elements[:8])
                lines.append("")
            if s.recommendations:
                lines.append("**Recommendations:**")
                lines.extend(f"- {r}" for r in s.recommendations[:5])
            parts.append(self._result_block("SEO Audit", s.score, lines))

        # Duplicate
        if hasattr(report.duplicate, 'score'):
            d = report.duplicate
            lines = [f"**Duplicate Paragraphs:** {d.duplicate_paragraphs}",
                     f"**Duplicate Headings:** {d.duplicate_headings}"]
            if d.repeated_sections:
                lines.append("**Repeated Sections:**")
                lines.extend(f"- {s}" for s in d.repeated_sections[:5])
            if d.merge_recommendations:
                lines.append("**Recommendations:**")
                lines.extend(f"- {r}" for r in d.merge_recommendations[:3])
            parts.append(self._result_block("Duplicate Content", d.score, lines))

        # Headings
        if hasattr(report.headings, 'score'):
            h = report.headings
            lines = [f"**H1 Count:** {h.h1_count}"]
            if h.hierarchy_issues:
                lines.append("**Hierarchy Issues:**")
                lines.extend(f"- {issue}" for issue in h.hierarchy_issues[:5])
            if h.skipped_levels:
                lines.append(f"**Skipped Levels:** {', '.join(h.skipped_levels)}")
            parts.append(self._result_block("Heading Structure", h.score, lines))

        # Completeness
        if hasattr(report.completeness, 'score'):
            c = report.completeness
            checks = [
                ("Introduction", c.has_introduction),
                ("Core Explanation", c.has_core_explanation),
                ("Examples", c.has_examples),
                ("Best Practices", c.has_best_practices),
                ("Benefits", c.has_benefits),
                ("Limitations", c.has_limitations),
                ("FAQ", c.has_faq),
                ("Summary", c.has_summary),
                ("Call-to-Action", c.has_call_to_action),
            ]
            lines = [f"**{'✓' if v else '✗'} {label}**" for label, v in checks]
            if c.missing_sections:
                lines.append("**Missing Sections:**")
                lines.extend(f"- {s}" for s in c.missing_sections)
            if c.suggested_topics:
                lines.append("**Suggested Topics:**")
                lines.extend(f"- {t}" for t in c.suggested_topics[:5])
            parts.append(self._result_block("Content Completeness", c.score, lines))

        # Hallucination
        if hasattr(report.hallucination, 'score'):
            h = report.hallucination
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            lines = [f"**Risk Level:** {risk_emoji.get(h.risk_level.value, '⚪')} {h.risk_level.value.title()}",
                     f"**Unsupported Claims:** {h.unsupported_claims}",
                     f"**Unverifiable Statistics:** {h.unverifiable_statistics}",
                     f"**Potentially Fabricated References:** {h.fabricated_references}"]
            if h.flagged_statements:
                lines.append("**Flagged Statements:**")
                for stmt in h.flagged_statements[:5]:
                    lines.append(f"- ⚠ `{stmt.get('statement', '')[:80]}...` — {stmt.get('reason', '')}")
            if h.recommendations:
                lines.append("**Recommendations:**")
                lines.extend(f"- {r}" for r in h.recommendations[:5])
            parts.append(self._result_block("Hallucination Risk", h.score, lines))

        # EEAT
        if hasattr(report.eeat, 'score'):
            e = report.eeat
            lines = [f"**Experience:** {e.experience_score:.0f}/100",
                     f"**Expertise:** {e.expertise_score:.0f}/100",
                     f"**Authoritativeness:** {e.authoritativeness_score:.0f}/100",
                     f"**Trustworthiness:** {e.trustworthiness_score:.0f}/100"]
            if e.weak_areas:
                lines.append("**Weak Areas:**")
                lines.extend(f"- {w}" for w in e.weak_areas)
            if e.recommendations:
                lines.append("**Recommendations:**")
                lines.extend(f"- {r}" for r in e.recommendations[:5])
            parts.append(self._result_block("E-E-A-T Evaluation", e.score, lines))

        # AI Detection
        if hasattr(report.ai_detection, 'score'):
            a = report.ai_detection
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            lines = [f"**Risk Level:** {risk_emoji.get(a.risk_level, '⚪')} {a.risk_level.title()}",
                     f"**Lexical Diversity:** {a.lexical_diversity_score:.1%}",
                     f"**Sentence Variety:** {a.avg_sentence_length_variety:.1f}/100"]
            if a.repetitive_phrases:
                lines.append(f"**Repetitive Phrases ({len(a.repetitive_phrases)}):**")
                lines.extend(f"- '{p}'" for p in a.repetitive_phrases[:5])
            if a.recommendations:
                lines.append("**Recommendations:**")
                lines.extend(f"- {r}" for r in a.recommendations[:5])
            parts.append(self._result_block("AI Detection Risk", a.score, lines))

        # Content Quality
        if hasattr(report.content_quality, 'score'):
            cq = report.content_quality
            lines = [f"**Clarity:** {cq.clarity_score:.0f}/100",
                     f"**Logical Flow:** {cq.logical_flow_score:.0f}/100",
                     f"**Actionability:** {cq.actionability_score:.0f}/100",
                     f"**Originality:** {cq.originality_score:.0f}/100",
                     f"**Engagement:** {cq.engagement_score:.0f}/100",
                     f"**Tone Consistency:** {cq.tone_consistency_score:.0f}/100"]
            parts.append(self._result_block("Content Quality", cq.score, lines))

        # Accessibility
        if hasattr(report.accessibility, 'score'):
            a = report.accessibility
            lines = [f"**Images Missing ALT Text:** {a.images_missing_alt}"]
            if a.heading_structure_issues:
                lines.append("**Heading Issues:**")
                lines.extend(f"- {i}" for i in a.heading_structure_issues[:3])
            if a.link_text_issues:
                lines.append("**Link Issues:**")
                lines.extend(f"- {i}" for i in a.link_text_issues[:3])
            if a.recommendations:
                lines.append("**Recommendations:**")
                lines.extend(f"- {r}" for r in a.recommendations[:3])
            parts.append(self._result_block("Accessibility", a.score, lines))

        # Linking
        if hasattr(report.internal_linking, 'score'):
            il = report.internal_linking
            lines = [f"**Score:** {il.score:.0f}/100",
                     f"**Internal Links Found:** {il.internal_link_count}"]
            if il.poor_anchor_text:
                lines.append("**Poor Anchor Text:**")
                lines.extend(f"- {a}" for a in il.poor_anchor_text[:3])
            if il.recommendations:
                lines.extend(f"- {r}" for r in il.recommendations[:3])
            parts.append(self._result_block("Internal Linking", il.score, lines))

        if hasattr(report.external_linking, 'score'):
            el = report.external_linking
            lines = [f"**Score:** {el.score:.0f}/100",
                     f"**External Links Found:** {el.external_link_count}"]
            if el.broken_links:
                lines.append("**Broken/Non-HTTPS Links:**")
                lines.extend(f"- {b}" for b in el.broken_links[:3])
            if el.recommendations:
                lines.extend(f"- {r}" for r in el.recommendations[:3])
            parts.append(self._result_block("External Linking", el.score, lines))

        # Fact Consistency
        if hasattr(report.fact_consistency, 'score'):
            fc = report.fact_consistency
            lines = [f"**Conflicting Statements:** {len(fc.conflicting_statements)}"]
            if fc.conflicting_statements:
                lines.extend(f"- {s}" for s in fc.conflicting_statements[:5])
            if fc.timeline_inconsistencies:
                lines.append("**Timeline Issues:**")
                lines.extend(f"- {t}" for t in fc.timeline_inconsistencies[:3])
            if fc.number_inconsistencies:
                lines.append("**Number Inconsistencies:**")
                lines.extend(f"- {n}" for n in fc.number_inconsistencies[:3])
            parts.append(self._result_block("Fact Consistency", fc.score, lines))

        return "\n".join(parts)

    def _issues_section(self, report: QualityReport) -> str:
        parts: list[str] = []

        severity_order = [
            (IssueSeverity.CRITICAL, "Critical", report.critical_issues),
            (IssueSeverity.HIGH, "High", report.high_issues),
            (IssueSeverity.MEDIUM, "Medium", report.medium_issues),
            (IssueSeverity.LOW, "Low", report.low_issues),
        ]

        for sev, label, issues in severity_order:
            if issues:
                parts.append(f"### {label}\n")
                for i, issue in enumerate(issues[:5], 1):
                    parts.append(f"**{i}. {issue.description}**")
                    if issue.location:
                        parts.append(f"   - **Location:** {issue.location}")
                    if issue.why_it_matters:
                        parts.append(f"   - **Why:** {issue.why_it_matters}")
                    if issue.recommended_fix:
                        parts.append(f"   - **Fix:** {issue.recommended_fix}")
                    parts.append("")

        if not any([report.critical_issues, report.high_issues, report.medium_issues, report.low_issues]):
            parts.append("No issues found.")

        return "\n".join(parts)

    def _recommendations(self, report: QualityReport) -> str:
        parts: list[str] = []

        if report.must_fix:
            parts.append("### 🔴 Must Fix\n")
            for i, rec in enumerate(report.must_fix, 1):
                parts.append(f"{i}. {rec}")
            parts.append("")

        if report.should_improve:
            parts.append("### 🟡 Should Improve\n")
            for i, rec in enumerate(report.should_improve, 1):
                parts.append(f"{i}. {rec}")
            parts.append("")

        if report.nice_to_have:
            parts.append("### 🟢 Nice to Have\n")
            for i, rec in enumerate(report.nice_to_have, 1):
                parts.append(f"{i}. {rec}")
            parts.append("")

        if not any([report.must_fix, report.should_improve, report.nice_to_have]):
            parts.append("No recommendations. Content meets quality standards.")

        return "\n".join(parts)

    def _decision(self, report: QualityReport) -> str:
        emoji = {
            PublishDecision.ENTERPRISE_READY: "✅",
            PublishDecision.PUBLISH_READY: "✅",
            PublishDecision.MINOR_REVISIONS: "⚠",
            PublishDecision.MAJOR_REVISIONS: "⚠",
            PublishDecision.REJECT: "❌",
        }
        e = emoji.get(report.publish_decision, "❓")
        label = report.publish_decision.value.replace("_", " ").title()
        return f"### {e} {label}\n\nOverall Score: **{report.overall_score:.0f}/100**"

    def _result_block(self, title: str, score: float, lines: list[str | list]) -> str:
        emoji = self._score_emoji(score)
        header = f"### {emoji} {title} — **{score:.0f}/100**\n"
        body_lines: list[str] = []
        for item in lines:
            if isinstance(item, list):
                body_lines.extend(str(x) for x in item)
            else:
                body_lines.append(str(item))
        return header + "\n".join(body_lines) + "\n\n"

    @staticmethod
    def _score_emoji(score: float) -> str:
        if score >= 90:
            return "🟢"
        if score >= 70:
            return "🟡"
        return "🔴"

    @staticmethod
    def _status_emoji(status: str) -> str:
        mapping = {
            "excellent": "🟢",
            "good": "🟢",
            "fair": "🟡",
            "poor": "🔴",
            "fail": "🔴",
        }
        return mapping.get(status, "⚪")

    @staticmethod
    def _decision_emoji(decision: PublishDecision) -> str:
        mapping = {
            PublishDecision.ENTERPRISE_READY: "✅",
            PublishDecision.PUBLISH_READY: "✅",
            PublishDecision.MINOR_REVISIONS: "⚠️",
            PublishDecision.MAJOR_REVISIONS: "⚠️",
            PublishDecision.REJECT: "❌",
        }
        return mapping.get(decision, "❓")
