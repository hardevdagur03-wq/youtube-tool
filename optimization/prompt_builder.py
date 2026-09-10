"""Dynamic Prompt Builder — constructs targeted optimization prompts per type."""

from __future__ import annotations
import logging
from typing import Any

from optimization.optimization_models import (
    OptimizationContext, OptimizationPrompt, OptimizationType,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS: dict[OptimizationType, str] = {
    OptimizationType.SEO: (
        "You are an expert SEO content optimizer. Your task is to improve the SEO score of the given section "
        "while preserving its original meaning, facts, and structure. "
        "Focus on keyword placement, semantic relevance, heading optimization, and search intent alignment. "
        "Do NOT add fabricated statistics or claims. Do NOT change verified facts. "
        "Maintain natural readability and professional tone."
    ),
    OptimizationType.GRAMMAR: (
        "You are an expert copy editor. Your task is to fix grammar, spelling, punctuation, and sentence structure errors. "
        "Preserve the original meaning, tone, and voice. Do not rewrite more than necessary. "
        "Fix run-on sentences, sentence fragments, subject-verb agreement, and capitalization. "
        "Maintain technical accuracy and professional tone."
    ),
    OptimizationType.READABILITY: (
        "You are an expert readability optimizer. Simplify sentence structure, improve transitions, "
        "and enhance clarity while preserving all technical content, facts, and meaning. "
        "Reduce average sentence length. Improve paragraph flow. Add transition words where appropriate. "
        "Maintain professional tone and accuracy."
    ),
    OptimizationType.HALLUCINATION: (
        "You are an expert fact-checker and content corrector. Remove or rewrite unsupported claims, "
        "unverifiable statistics, and fabricated references. Cross-check against the provided context. "
        "Only keep statements that are supported by the knowledge graph or analysis. "
        "Preserve all verified information and natural flow."
    ),
    OptimizationType.KEYWORD: (
        "You are an expert keyword optimization specialist. Naturally incorporate the target keywords "
        "into the content without keyword stuffing. Improve keyword density and placement. "
        "Add semantically related terms (LSI keywords). Maintain natural readability and professional tone."
    ),
    OptimizationType.DUPLICATE: (
        "You are an expert content deduplication specialist. Rewrite the section to eliminate "
        "duplicate or repetitive content while preserving all unique information. "
        "Ensure each sentence adds new value. Maintain professional tone and accuracy."
    ),
    OptimizationType.PASSIVE_VOICE: (
        "You are an expert writing style optimizer. Convert passive voice constructions to active voice "
        "wherever possible. Maintain the original meaning and factual accuracy. "
        "Make the writing more direct, engaging, and authoritative."
    ),
    OptimizationType.FAQ: (
        "You are an expert FAQ content creator. Generate clear, concise FAQ entries that address "
        "common user questions. Each Q&A pair should provide genuine value. "
        "Use the knowledge graph and outline for context."
    ),
    OptimizationType.CTA: (
        "You are an expert conversion copywriter. Generate a compelling call-to-action that "
        "encourages reader engagement. Make it specific, actionable, and aligned with the content's purpose. "
        "Maintain professional tone."
    ),
    OptimizationType.SUMMARY: (
        "You are an expert content summarizer. Generate a concise yet comprehensive summary of the key takeaways. "
        "Cover the main points without introducing new information. "
        "Make it scannable and valuable for readers who skim."
    ),
    OptimizationType.MARKDOWN: (
        "You are an expert Markdown formatter. Fix broken Markdown syntax: repair table alignment, "
        "fix heading hierarchy, correct image/link syntax, ensure proper code block formatting. "
        "Preserve all content and meaning. Only fix formatting issues."
    ),
    OptimizationType.STRUCTURE: (
        "You are an expert content structure optimizer. Improve heading hierarchy, section organization, "
        "and logical flow. Fix skipped heading levels. Ensure consistent structure. "
        "Preserve all content while improving organization."
    ),
    OptimizationType.STYLE: (
        "You are an expert style editor. Improve the professional tone, brand voice consistency, "
        "and reader engagement. Make the content more compelling while preserving all facts, "
        "statistics, and technical accuracy. Maintain natural flow."
    ),
    OptimizationType.COMPLETENESS: (
        "You are an expert content completeness optimizer. Add missing elements such as examples, "
        "explanations, benefits, or context to make the section more comprehensive. "
        "Do not add fabricated information. Use the provided context for guidance."
    ),
}


class PromptBuilder:
    """Builds targeted optimization prompts per optimization type."""

    def build_prompt(
        self,
        context: OptimizationContext,
        optimization_type: OptimizationType,
        improvement_goals: list[str] | None = None,
    ) -> OptimizationPrompt:
        system_prompt = self._build_system_prompt(optimization_type, context)
        user_prompt = self._build_user_prompt(context, optimization_type, improvement_goals)
        goals = improvement_goals or self._default_goals(optimization_type)
        target_scores = self._target_scores(optimization_type)

        return OptimizationPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            optimization_type=optimization_type,
            context=context,
            improvement_goals=goals,
            target_scores=target_scores,
        )

    def _build_system_prompt(self, opt_type: OptimizationType, context: OptimizationContext) -> str:
        base = SYSTEM_PROMPTS.get(opt_type, "You are an expert content optimizer.")
        parts = [base]

        if context.primary_keyword:
            parts.append(f"\n\nPrimary Keyword: '{context.primary_keyword}'")
        if context.secondary_keywords:
            parts.append(f"Secondary Keywords: {', '.join(context.secondary_keywords)}")

        if context.blog_title:
            parts.append(f"Blog Title: {context.blog_title}")

        parts.append("\n\nCRITICAL RULES:")
        parts.append("- Preserve all verified facts, statistics, examples, tables, images, code blocks, and references.")
        parts.append("- Do NOT add fabricated statistics, claims, or references.")
        parts.append("- Maintain the original meaning and technical accuracy.")
        parts.append("- Keep the same heading level and section structure.")
        parts.append("- Return ONLY the optimized section content. Do not include the heading unless asked.")
        parts.append("- Do not wrap in code blocks or markdown fences.")

        return "\n".join(parts)

    def _build_user_prompt(
        self,
        context: OptimizationContext,
        opt_type: OptimizationType,
        improvement_goals: list[str] | None,
    ) -> str:
        parts: list[str] = []

        parts.append("Please optimize the following section.\n")

        if improvement_goals:
            parts.append("Improvement Goals:")
            for g in improvement_goals:
                parts.append(f"- {g}")
            parts.append("")

        if context.issues:
            parts.append("Issues to address:")
            for issue in context.issues[:5]:
                desc = issue.get("description", "") if isinstance(issue, dict) else str(issue)
                parts.append(f"- {desc}")
            parts.append("")

        if context.recommendations:
            parts.append("Recommendations to follow:")
            for rec in context.recommendations[:3]:
                desc = rec.get("description", "") if isinstance(rec, dict) else str(rec)
                parts.append(f"- {desc}")
            parts.append("")

        if opt_type == OptimizationType.SEO:
            kw_info = []
            if context.primary_keyword:
                kw_info.append(f"Primary: '{context.primary_keyword}'")
            if context.secondary_keywords:
                kw_info.append(f"Secondary: {', '.join(context.secondary_keywords)}")
            if kw_info:
                parts.append(f"Keywords: {' | '.join(kw_info)}")
            if context.seo_plan and isinstance(context.seo_plan, dict):
                heading_strategy = context.seo_plan.get("heading_strategy", {}) if isinstance(context.seo_plan, dict) else {}
                if isinstance(heading_strategy, dict) and heading_strategy.get("suggestions"):
                    parts.append(f"Heading suggestions: {', '.join(heading_strategy['suggestions'][:3])}")
            parts.append("")

        if opt_type == OptimizationType.HALLUCINATION:
            kg = context.knowledge_graph
            if isinstance(kg, dict):
                facts = kg.get("facts", []) if isinstance(kg, dict) else []
                if facts:
                    parts.append("Verified facts from knowledge graph:")
                    for fact in facts[:5]:
                        if isinstance(fact, dict):
                            parts.append(f"- {fact.get('statement', fact.get('fact', ''))}")
                stats = kg.get("statistics", []) if isinstance(kg, dict) else []
                if stats:
                    parts.append("Verified statistics:")
                    for stat in stats[:3]:
                        if isinstance(stat, dict):
                            parts.append(f"- {stat.get('value', stat.get('statistic', ''))}")
            parts.append("")

        parts.append("SECTION CONTENT:")
        parts.append(context.section_text)

        if context.outline_section and isinstance(context.outline_section, dict):
            parts.append("\nOutline guidance:")
            desc = context.outline_section.get("description", "")
            if desc:
                parts.append(desc)
            key_points = context.outline_section.get("key_points", context.outline_section.get("points", []))
            if key_points:
                parts.append("Key points to cover:")
                for kp in key_points[:3]:
                    parts.append(f"- {kp}")

        return "\n".join(parts)

    def _default_goals(self, opt_type: OptimizationType) -> list[str]:
        goals = {
            OptimizationType.SEO: ["Improve keyword placement", "Enhance semantic coverage", "Optimize for search intent"],
            OptimizationType.GRAMMAR: ["Fix grammar errors", "Correct spelling", "Improve punctuation", "Fix sentence structure"],
            OptimizationType.READABILITY: ["Reduce sentence length", "Improve paragraph transitions", "Simplify complex sentences"],
            OptimizationType.HALLUCINATION: ["Remove unsupported claims", "Verify statistics", "Remove fabricated references"],
            OptimizationType.KEYWORD: ["Improve keyword density (0.5-2.5%)", "Add LSI keywords", "Natural keyword integration"],
            OptimizationType.DUPLICATE: ["Remove repetitive content", "Ensure unique value per sentence"],
            OptimizationType.PASSIVE_VOICE: ["Convert to active voice", "Make writing more direct"],
            OptimizationType.FAQ: ["Generate clear Q&A pairs", "Address user intent"],
            OptimizationType.CTA: ["Create compelling action prompt", "Match content purpose"],
            OptimizationType.SUMMARY: ["Cover key takeaways", "Be concise yet comprehensive"],
            OptimizationType.MARKDOWN: ["Fix broken syntax", "Proper table formatting", "Valid heading hierarchy"],
            OptimizationType.STRUCTURE: ["Fix heading levels", "Improve logical flow"],
            OptimizationType.STYLE: ["Improve professional tone", "Enhance engagement"],
            OptimizationType.COMPLETENESS: ["Add missing elements", "Improve section depth"],
        }
        return goals.get(opt_type, ["Improve content quality"])

    def _target_scores(self, opt_type: OptimizationType) -> dict[str, float]:
        return {
            OptimizationType.SEO: {"seo": 90.0},
            OptimizationType.GRAMMAR: {"grammar": 95.0},
            OptimizationType.READABILITY: {"readability": 90.0},
            OptimizationType.HALLUCINATION: {"hallucination_risk": 90.0},
            OptimizationType.KEYWORD: {"keyword_optimization": 85.0},
            OptimizationType.PASSIVE_VOICE: {"grammar": 95.0},
            OptimizationType.MARKDOWN: {"markdown_quality": 95.0},
        }.get(opt_type, {"overall": 90.0})
