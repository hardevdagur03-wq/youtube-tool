"""CTA generator — Phase 7. Specialized call-to-action generation."""

from __future__ import annotations
import logging
from typing import Any

from modules.ai.provider import LLMProvider
from modules.ai.prompt_builder import build_cta_prompt, get
from modules.ai.response_parser import parse_blog

logger = logging.getLogger(__name__)


def extract_cta(data: dict[str, Any]) -> str:
    return str(data.get("call_to_action", data.get("cta", ""))).strip()
