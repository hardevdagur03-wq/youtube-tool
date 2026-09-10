"""Prompt builder — constructs optimized prompts for content analysis."""

from __future__ import annotations

from prompts.analysis_prompt import ANALYSIS_PROMPT, SYSTEM_PROMPT, PROMPT_VERSION


_MAX_TRANSCRIPT_CHARS = 80000


def build_analysis_prompt(
    transcript: str,
    video_id: str,
    categories: str = "",
    language: str = "en",
) -> str:
    """Build the analysis prompt with transcript truncation."""
    truncated = transcript[:_MAX_TRANSCRIPT_CHARS]
    if len(transcript) > _MAX_TRANSCRIPT_CHARS:
        truncated += "\n\n[Note: Transcript was truncated due to length.]"

    return ANALYSIS_PROMPT.format(
        transcript=truncated,
        video_id=video_id,
        categories=categories,
        language=language,
    )


def get_system_prompt() -> str:
    return SYSTEM_PROMPT


def get_prompt_version() -> str:
    return PROMPT_VERSION
