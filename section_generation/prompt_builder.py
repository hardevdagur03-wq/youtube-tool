"""Dynamic Prompt Builder — builds optimized prompts for every section type.

Each section receives only the context it needs. No full transcript or
entire knowledge graph is ever sent to a single prompt.
"""

from __future__ import annotations

import logging
from typing import Any

from section_generation.section_models import (
    SectionContext,
    SectionPrompt,
    SectionType,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert SEO content writer and blog author. "
    "Write in a conversational, professional tone. "
    "Use markdown formatting. "
    "Be factual — only use the provided context. "
    "Do not hallucinate statistics, quotes, or facts. "
    "Naturally integrate keywords without stuffing. "
    "Keep paragraphs concise (3-5 sentences). "
    "Output only the section content in markdown. "
    "Do NOT include a heading if one is already provided."
)

SECTION_PROMPT_TEMPLATES: dict[SectionType, str] = {
    SectionType.INTRODUCTION: (
        "Write the introduction for a blog post titled \"{primary_keyword}\".\n\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "KEYWORD: {primary_keyword}\n"
        "INTENT: {search_intent}\n\n"
        "CONTEXT:\n"
        "{pain_points_context}"
        "{supporting_facts_context}"
        "{statistics_context}"
        "{unique_value_context}"
        "\nWriting guidelines:\n"
        "- Start with a hook that grabs attention\n"
        "- Briefly state the problem or opportunity\n"
        "- Explain what the reader will learn\n"
        "- Set expectations for the article\n"
        "- Target {word_count} words\n"
        "- Do NOT include a heading"
    ),
    SectionType.BODY: (
        "Write a blog section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n"
        "RELATED KEYWORDS: {keywords_str}\n\n"
        "CONTEXT:\n"
        "{key_concepts_context}"
        "{facts_context}"
        "{statistics_context}"
        "{examples_context}"
        "{quotes_context}"
        "{definitions_context}"
        "\nWriting guidelines:\n"
        "- Support claims with specific details from context\n"
        "- Naturally include related keywords\n"
        "- Use examples where helpful\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.PROBLEM: (
        "Write a section explaining a problem or challenge.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{pain_points_context}"
        "{facts_context}"
        "{statistics_context}"
        "{quotes_context}"
        "\nWriting guidelines:\n"
        "- Describe the problem clearly\n"
        "- Explain why it matters to the reader\n"
        "- Use statistics and facts from context\n"
        "- Build urgency or importance\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.STEP_BY_STEP: (
        "Write a step-by-step guide section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{facts_context}"
        "{key_concepts_context}"
        "{examples_context}"
        "{solutions_context}"
        "\nWriting guidelines:\n"
        "- Number each step\n"
        "- Be specific and actionable\n"
        "- Include examples where helpful\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.COMPARISON: (
        "Write a comparison section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{facts_context}"
        "{key_concepts_context}"
        "{examples_context}"
        "\nWriting guidelines:\n"
        "- Compare options, tools, or approaches\n"
        "- Highlight pros and cons\n"
        "- Use a table if helpful\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.DEFINITION: (
        "Write a definitions or key terms section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{definitions_context}"
        "{key_concepts_context}"
        "{facts_context}"
        "\nWriting guidelines:\n"
        "- Define each term clearly\n"
        "- Provide context for why each term matters\n"
        "- Use bold for term names (**term**)\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.BENEFITS: (
        "Write a benefits section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{facts_context}"
        "{statistics_context}"
        "{key_concepts_context}"
        "{solutions_context}"
        "\nWriting guidelines:\n"
        "- List and explain each benefit\n"
        "- Connect benefits to reader pain points\n"
        "- Use specific evidence from context\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.USE_CASES: (
        "Write a use cases section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{examples_context}"
        "{facts_context}"
        "{key_concepts_context}"
        "\nWriting guidelines:\n"
        "- Describe real-world scenarios\n"
        "- Show how each use case solves problems\n"
        "- Be practical and relatable\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.EXAMPLES: (
        "Write an examples section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{examples_context}"
        "{facts_context}"
        "{key_concepts_context}"
        "\nWriting guidelines:\n"
        "- Provide concrete, specific examples\n"
        "- Explain what makes each example effective\n"
        "- Use code blocks if applicable\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.TABLE: (
        "Write a table section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{facts_context}"
        "{key_concepts_context}"
        "\nWriting guidelines:\n"
        "- Create a markdown table with clear headers\n"
        "- Include a brief introductory sentence\n"
        "- Keep rows clear and scannable\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.FAQ: (
        "Write the FAQ section for a blog post.\n\n"
        "TOPIC: {primary_keyword}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "INTENT: {search_intent}\n\n"
        "CONTEXT:\n"
        "{definitions_context}"
        "{facts_context}"
        "{statistics_context}"
        "\nGenerate 3-6 FAQ items. Each item must have a question and a clear answer.\n"
        "Only include questions that the provided context actually answers.\n"
        "Format as markdown:\n"
        "### Question?\n"
        "Answer here.\n"
        "Target {word_count} words total.\n"
        "Do NOT include a section heading."
    ),
    SectionType.CONCLUSION: (
        "Write the conclusion for a blog post about \"{primary_keyword}\".\n\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "KEYWORD: {primary_keyword}\n\n"
        "KEY TAKEAWAYS:\n"
        "{supporting_facts_context}"
        "{unique_value_context}"
        "\nWriting guidelines:\n"
        "- Summarize the main points briefly\n"
        "- Reinforce the key takeaway for the reader\n"
        "- End with a forward-looking statement\n"
        "- Target {word_count} words\n"
        "- Do NOT include a heading"
    ),
    SectionType.CTA: (
        "Write a call-to-action for a blog post about \"{primary_keyword}\".\n\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "\nWriting guidelines:\n"
        "- Write 1-3 sentences\n"
        "- Encourage: subscribe, share, comment, or read more\n"
        "- Be natural and not salesy\n"
        "- Match the article tone"
    ),
    SectionType.SUMMARY: (
        "Write a summary section for a blog post.\n\n"
        "TOPIC: {primary_keyword}\n"
        "TARGET AUDIENCE: {target_audience}\n\n"
        "KEY POINTS:\n"
        "{supporting_facts_context}"
        "{key_concepts_context}"
        "\nWriting guidelines:\n"
        "- Recap the most important points\n"
        "- Keep it brief (3-5 bullet points or a short paragraph)\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.DRAWBACKS: (
        "Write a drawbacks or limitations section.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "TARGET AUDIENCE: {target_audience}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{facts_context}"
        "{key_concepts_context}"
        "\nWriting guidelines:\n"
        "- Be honest about limitations\n"
        "- Provide balanced perspective\n"
        "- Suggest mitigations where possible\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
    SectionType.QUOTE: (
        "Write a key insights section featuring notable quotes.\n\n"
        "SECTION HEADING: {heading}\n"
        "GOAL: {goal}\n"
        "PRIMARY KEYWORD: {primary_keyword}\n\n"
        "CONTEXT:\n"
        "{quotes_context}"
        "{facts_context}"
        "\nWriting guidelines:\n"
        "- Present each quote with context\n"
        "- Explain why each insight matters\n"
        "- Use blockquote formatting (>)\n"
        "- Target {word_count} words\n"
        "- Start with the heading provided"
    ),
}


class PromptBuilder:
    """Builds optimized prompts for each section type.

    Every section gets a prompt with only the context it needs.
    """

    def build(
        self,
        ctx: SectionContext,
        section_type: SectionType | None = None,
    ) -> SectionPrompt:
        st = section_type or ctx.section_type
        template = SECTION_PROMPT_TEMPLATES.get(st)
        if template is None:
            template = SECTION_PROMPT_TEMPLATES[SectionType.BODY]

        user_prompt = self._render(template, ctx)
        system = self._build_system(ctx, st)

        prompt = SectionPrompt(
            system_prompt=system,
            user_prompt=user_prompt,
            template_version="1.0.0",
            prompt_tokens_estimate=len(system + user_prompt) // 4,
        )
        return prompt

    def _build_system(
        self,
        ctx: SectionContext,
        section_type: SectionType,
    ) -> str:
        parts = [SYSTEM_PROMPT]

        if ctx.tone:
            parts.append(f"Tone: {ctx.tone}.")
        if ctx.writing_style:
            parts.append(f"Style: {ctx.writing_style}.")
        if ctx.brand_voice:
            parts.append(f"Voice: {ctx.brand_voice}.")

        if ctx.target_audience:
            parts.append(f"Write for: {ctx.target_audience}.")

        if ctx.content_angle:
            parts.append(f"Angle: {ctx.content_angle}.")

        parts.append("Output only valid markdown content.")

        return "\n".join(parts)

    def _render(self, template: str, ctx: SectionContext) -> str:
        context_sections = {
            "key_concepts_context": self._list_context("Key concepts:", ctx.key_concepts),
            "facts_context": self._list_context("Supporting facts:", ctx.facts),
            "statistics_context": self._list_context("Statistics:", ctx.statistics),
            "pain_points_context": self._list_context("Pain points:", ctx.pain_points),
            "solutions_context": self._list_context("Solutions:", ctx.solutions),
            "examples_context": self._list_context("Examples:", ctx.examples),
            "quotes_context": self._list_context("Notable quotes:", ctx.quotes),
            "definitions_context": self._definitions_context(ctx.definitions),
            "supporting_facts_context": self._list_context("Key takeaways:", ctx.supporting_facts),
            "unique_value_context": (
                f"Unique value: {ctx.unique_value}\n" if ctx.unique_value else ""
            ),
        }

        format_args = {
            "heading": ctx.heading,
            "goal": ctx.goal or "Provide valuable information to the reader.",
            "primary_keyword": ctx.primary_keyword or "",
            "target_audience": ctx.target_audience or "general readers",
            "search_intent": ctx.search_intent or "informational",
            "word_count": str(ctx.target_word_count),
            "keywords_str": ", ".join(ctx.keywords[:10]),
            **{k: v for k, v in context_sections.items()},
        }

        try:
            return template.format(**format_args)
        except KeyError as exc:
            logger.warning("Missing template key: %s", exc)
            return template

    @staticmethod
    def _list_context(header: str, items: list[str]) -> str:
        if not items:
            return ""
        lines = [f"- {item}" for item in items[:10]]
        return f"{header}\n" + "\n".join(lines) + "\n"

    @staticmethod
    def _definitions_context(definitions: list[dict[str, str]]) -> str:
        if not definitions:
            return ""
        lines = []
        for d in definitions[:5]:
            term = d.get("term", "")
            definition = d.get("definition", "")
            if term and definition:
                lines.append(f"- {term}: {definition}")
        if not lines:
            return ""
        return "Definitions:\n" + "\n".join(lines) + "\n"
