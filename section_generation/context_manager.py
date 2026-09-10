"""Context Manager — loads only the relevant context for each section.

Prevents unnecessary token usage by selecting only the data needed
for the specific section being generated. Never sends the entire
transcript or full knowledge graph to every prompt.
"""

from __future__ import annotations

import logging
from typing import Any

from section_generation.section_models import (
    SectionContext,
    SectionType,
)

logger = logging.getLogger(__name__)


class ContextManager:
    """Loads minimal context for each section from existing artifacts.

    Consumes outline.json, knowledge_graph.json, seo_plan.json, analysis.json.
    """

    def __init__(self) -> None:
        self._outline: dict[str, Any] = {}
        self._knowledge_graph: dict[str, Any] = {}
        self._seo_plan: dict[str, Any] = {}
        self._analysis: dict[str, Any] = {}
        self._project: dict[str, Any] = {}

    def load(
        self,
        outline: dict[str, Any] | None = None,
        knowledge_graph: dict[str, Any] | None = None,
        seo_plan: dict[str, Any] | None = None,
        analysis: dict[str, Any] | None = None,
        project: dict[str, Any] | None = None,
    ) -> None:
        self._outline = outline or {}
        self._knowledge_graph = knowledge_graph or {}
        self._seo_plan = seo_plan or {}
        self._analysis = analysis or {}
        self._project = project or {}
        logger.debug(
            "ContextManager loaded: outline=%s, kg=%s, seo=%s, analysis=%s, project=%s",
            "yes" if outline else "no",
            "yes" if knowledge_graph else "no",
            "yes" if seo_plan else "no",
            "yes" if analysis else "no",
            "yes" if project else "no",
        )

    def get_context_for_section(
        self,
        section_type: SectionType,
        section_plan: dict[str, Any] | None = None,
        order: int = 0,
    ) -> SectionContext:
        """Build the minimal context for a single section."""
        plan = section_plan or {}

        ctx = SectionContext(
            section_type=section_type,
            heading=plan.get("heading", self._default_heading(section_type)),
            goal=plan.get("goal", ""),
            order=order,
            target_word_count=plan.get("target_word_count", self._default_word_count(section_type)),
            keywords=list(plan.get("keywords", [])),
            entities=list(plan.get("entities", [])),
            facts=list(plan.get("supporting_facts", [])),
            statistics=list(plan.get("statistics", [])),
            pain_points=list(plan.get("pain_points", [])),
            solutions=list(plan.get("solutions", [])),
            definitions=list(plan.get("definitions", [])),
            quotes=list(plan.get("quotes", [])),
            examples=list(plan.get("examples", [])),
            key_concepts=list(plan.get("key_concepts", [])),
            supporting_facts=list(plan.get("supporting_facts", [])),
        )

        self._enrich_from_seo(ctx)
        self._enrich_from_analysis(ctx)
        self._enrich_from_knowledge_graph(ctx, plan)
        self._enrich_from_outline(ctx, section_type)

        return ctx

    def _default_heading(self, section_type: SectionType) -> str:
        defaults = {
            SectionType.INTRODUCTION: "Introduction",
            SectionType.PROBLEM: "The Problem",
            SectionType.EXPLANATION: "Overview",
            SectionType.STEP_BY_STEP: "Step-by-Step Guide",
            SectionType.COMPARISON: "Comparison",
            SectionType.DEFINITION: "Key Definitions",
            SectionType.BENEFITS: "Benefits",
            SectionType.DRAWBACKS: "Drawbacks",
            SectionType.USE_CASES: "Use Cases",
            SectionType.EXAMPLES: "Examples",
            SectionType.CASE_STUDIES: "Case Studies",
            SectionType.TABLE: "Overview Table",
            SectionType.LIST: "Key Points",
            SectionType.CODE: "Code Example",
            SectionType.QUOTE: "Key Insights",
            SectionType.FAQ: "Frequently Asked Questions",
            SectionType.SUMMARY: "Summary",
            SectionType.CONCLUSION: "Conclusion",
            SectionType.CTA: "Next Steps",
            SectionType.BODY: "Details",
        }
        return defaults.get(section_type, "Details")

    def _default_word_count(self, section_type: SectionType) -> int:
        defaults = {
            SectionType.INTRODUCTION: 200,
            SectionType.PROBLEM: 250,
            SectionType.EXPLANATION: 300,
            SectionType.STEP_BY_STEP: 400,
            SectionType.COMPARISON: 300,
            SectionType.DEFINITION: 200,
            SectionType.BENEFITS: 250,
            SectionType.DRAWBACKS: 200,
            SectionType.USE_CASES: 300,
            SectionType.EXAMPLES: 250,
            SectionType.CASE_STUDIES: 350,
            SectionType.TABLE: 100,
            SectionType.LIST: 150,
            SectionType.CODE: 100,
            SectionType.QUOTE: 100,
            SectionType.FAQ: 300,
            SectionType.SUMMARY: 200,
            SectionType.CONCLUSION: 200,
            SectionType.CTA: 100,
            SectionType.BODY: 300,
        }
        return defaults.get(section_type, 250)

    def _enrich_from_seo(self, ctx: SectionContext) -> None:
        sp = self._seo_plan
        if not sp:
            return

        ks = sp.get("keyword_strategy", {})
        if isinstance(ks, dict):
            ctx.primary_keyword = ks.get("primary_keyword", "")
            secondary = ks.get("secondary_keywords", [])
            if isinstance(secondary, list):
                for kw in secondary:
                    if isinstance(kw, dict):
                        k = kw.get("keyword", "")
                        if k and k not in ctx.keywords:
                            ctx.keywords.append(k)

        intent = sp.get("search_intent", {})
        if isinstance(intent, dict):
            ctx.search_intent = intent.get("primary_intent", "informational")

        audience = sp.get("target_audience", {})
        if isinstance(audience, dict):
            ctx.target_audience = audience.get("primary_audience", "")

        cs = sp.get("content_strategy", {})
        if isinstance(cs, dict):
            ctx.content_angle = cs.get("content_angle", "")
            ctx.tone = "conversational"

        internal = sp.get("internal_links", [])
        if isinstance(internal, list):
            for link in internal:
                if isinstance(link, dict):
                    anchor = link.get("suggested_anchor", "")
                    if anchor and anchor not in ctx.internal_links:
                        ctx.internal_links.append(anchor)

        external = sp.get("external_links", [])
        if isinstance(external, list):
            for link in external:
                if isinstance(link, dict):
                    domain = link.get("suggested_domain", "")
                    if domain and domain not in ctx.external_links:
                        ctx.external_links.append(domain)

        competitor = sp.get("competitor_strategy", {})
        if isinstance(competitor, dict):
            ctx.unique_value = competitor.get("unique_value_proposition", "")

    def _enrich_from_analysis(self, ctx: SectionContext) -> None:
        ad = self._analysis
        if not ad:
            return

        if not ctx.primary_keyword:
            ctx.primary_keyword = ad.get("primary_topic", "")

        if not ctx.target_audience:
            ctx.target_audience = ad.get("target_audience", "")

        if not ctx.tone:
            ctx.tone = ad.get("tone", "conversational")

        pain_points = ad.get("pain_points", [])
        if isinstance(pain_points, list):
            for pp in pain_points:
                if isinstance(pp, str) and pp not in ctx.pain_points and len(ctx.pain_points) < 5:
                    ctx.pain_points.append(pp)

        key_takeaways = ad.get("key_takeaways", [])
        if isinstance(key_takeaways, list):
            for kt in key_takeaways:
                if isinstance(kt, str) and kt not in ctx.supporting_facts and len(ctx.supporting_facts) < 5:
                    ctx.supporting_facts.append(kt)

    def _enrich_from_knowledge_graph(
        self,
        ctx: SectionContext,
        plan: dict[str, Any],
    ) -> None:
        kg = self._knowledge_graph
        if not kg:
            return

        plan_entities = set(plan.get("entities", []))
        plan_facts = set(plan.get("supporting_facts", []))

        entities = kg.get("entities", [])
        if isinstance(entities, list):
            for ent in entities:
                if isinstance(ent, dict):
                    name = ent.get("name", "")
                    if plan_entities and name not in plan_entities:
                        continue
                    if name and name not in ctx.entities:
                        ctx.entities.append(name)

        facts = kg.get("facts", [])
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, dict):
                    stmt = fact.get("statement", "")
                    if plan_facts and stmt not in plan_facts:
                        continue
                    if stmt and stmt not in ctx.facts and len(ctx.facts) < 8:
                        ctx.facts.append(stmt)

        statistics = kg.get("statistics", [])
        if isinstance(statistics, list):
            for stat in statistics:
                if isinstance(stat, dict):
                    val = stat.get("value", "")
                    meaning = stat.get("meaning", "")
                    ctx_s = f"{val} {meaning}".strip()
                    if ctx_s and len(ctx.statistics) < 4:
                        ctx.statistics.append(ctx_s)

        pain_points_kg = kg.get("pain_points", [])
        if isinstance(pain_points_kg, list):
            for pp in pain_points_kg:
                if isinstance(pp, dict):
                    problem = pp.get("problem", "")
                    if problem and problem not in ctx.pain_points and len(ctx.pain_points) < 3:
                        ctx.pain_points.append(problem)

        definitions = kg.get("definitions", [])
        if isinstance(definitions, list):
            for d in definitions:
                if isinstance(d, dict):
                    term = d.get("term", "")
                    definition = d.get("definition", "")
                    if term and definition and len(ctx.definitions) < 4:
                        ctx.definitions.append({"term": term, "definition": definition})

        quotes = kg.get("quotes", [])
        if isinstance(quotes, list):
            for q in quotes:
                if isinstance(q, dict):
                    text = q.get("text", "")
                    speaker = q.get("speaker", "")
                    q_text = f'"{text}"' if not speaker else f'{speaker}: "{text}"'
                    if text and q_text not in ctx.quotes and len(ctx.quotes) < 3:
                        ctx.quotes.append(q_text)

    def _enrich_from_outline(
        self,
        ctx: SectionContext,
        section_type: SectionType,
    ) -> None:
        ol = self._outline
        if not ol:
            return

        if section_type == SectionType.INTRODUCTION:
            intro = ol.get("intro_plan", {})
            if isinstance(intro, dict):
                if not ctx.goal:
                    ctx.goal = intro.get("reader_promise", "")
                ctx.writing_style = "hook_approach"

        elif section_type == SectionType.FAQ:
            faqs = ol.get("faqs", [])
            if isinstance(faqs, list):
                for faq in faqs:
                    if isinstance(faq, dict):
                        q = faq.get("question", "")
                        a = faq.get("answer_summary", "")
                        if q and a:
                            ctx.definitions.append({"term": q, "definition": a})

        elif section_type == SectionType.CONCLUSION:
            summary = ol.get("summary_plan", {})
            if isinstance(summary, dict):
                takeaways = summary.get("key_takeaways", [])
                if isinstance(takeaways, list):
                    for t in takeaways:
                        if isinstance(t, str) and t not in ctx.supporting_facts:
                            ctx.supporting_facts.append(t)

        elif section_type == SectionType.CTA:
            ctas = ol.get("ctas", [])
            if isinstance(ctas, list):
                for cta in ctas:
                    if isinstance(cta, dict):
                        text = cta.get("text", "")
                        if text and not ctx.goal:
                            ctx.goal = text

        title = ol.get("title", {})
        if isinstance(title, dict):
            if not ctx.primary_keyword:
                ctx.primary_keyword = title.get("primary_title", "")

    def get_outline_section(self, order: int) -> dict[str, Any]:
        ol = self._outline
        sections = ol.get("sections", [])
        if isinstance(sections, list) and order < len(sections):
            sec = sections[order]
            if isinstance(sec, dict):
                return sec
        return {}

    def get_intro_plan(self) -> dict[str, Any]:
        ol = self._outline
        intro = ol.get("intro_plan", {})
        return intro if isinstance(intro, dict) else {}

    def get_faq_plan(self) -> list[dict[str, Any]]:
        ol = self._outline
        faqs = ol.get("faqs", [])
        return [f for f in faqs if isinstance(f, dict)]

    def get_cta_plan(self) -> list[dict[str, Any]]:
        ol = self._outline
        ctas = ol.get("ctas", [])
        return [c for c in ctas if isinstance(c, dict)]

    def get_summary_plan(self) -> dict[str, Any]:
        ol = self._outline
        summary = ol.get("summary_plan", {})
        return summary if isinstance(summary, dict) else {}
