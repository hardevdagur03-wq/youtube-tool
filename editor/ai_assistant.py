from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Callable

from editor.editor_models import (
    AIActionRequest, AIActionResponse, AIActionType, utc_now,
)

logger = logging.getLogger(__name__)


class AIAssistant:
    def __init__(self):
        self._llm_provider: Any = None
        self._change_listeners: list[Callable] = []

    def set_llm_provider(self, provider: Any) -> None:
        self._llm_provider = provider

    def execute(self, request: AIActionRequest) -> AIActionResponse:
        start_time = time.time()
        self._emit("ai_action_started", {"action_type": request.action_type.value})

        try:
            if self._llm_provider:
                result = self._call_llm(request)
            else:
                result = self._execute_local(request)

            elapsed = (time.time() - start_time) * 1000
            result.processing_time_ms = round(elapsed, 2)

            self._emit("ai_action_completed", {
                "action_type": request.action_type.value,
                "success": result.success,
                "processing_time_ms": result.processing_time_ms,
            })

            return result

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"AI action failed: {e}")
            response = AIActionResponse(
                success=False,
                action_type=request.action_type,
                original_text=request.text,
                error=str(e),
                processing_time_ms=round(elapsed, 2),
            )
            self._emit("ai_action_failed", {
                "action_type": request.action_type.value,
                "error": str(e),
            })
            return response

    def _call_llm(self, request: AIActionRequest) -> AIActionResponse:
        prompt = self._build_prompt(request)
        try:
            result = self._llm_provider.generate(prompt, temperature=request.temperature, max_tokens=request.max_tokens)
            return AIActionResponse(
                success=True,
                action_type=request.action_type,
                original_text=request.text,
                modified_text=result.text.strip(),
                explanation=result.explanation or "",
                tokens_used=result.tokens_used or 0,
            )
        except Exception as e:
            raise

    def _execute_local(self, request: AIActionRequest) -> AIActionResponse:
        text = request.text
        if not text:
            return AIActionResponse(
                success=False,
                action_type=request.action_type,
                error="No text provided for AI action",
            )

        modified = text

        if request.action_type == AIActionType.REWRITE:
            modified = self._local_rewrite(text, request.tone, request.instructions)
        elif request.action_type == AIActionType.EXPAND:
            modified = self._local_expand(text, request.instructions)
        elif request.action_type == AIActionType.SIMPLIFY:
            modified = self._local_simplify(text)
        elif request.action_type == AIActionType.SHORTEN:
            modified = self._local_shorten(text)
        elif request.action_type == AIActionType.FIX_GRAMMAR:
            modified = self._local_fix_grammar(text)
        elif request.action_type == AIActionType.IMPROVE_TONE:
            modified = self._local_improve_tone(text, request.tone)
        elif request.action_type == AIActionType.SUMMARIZE:
            modified = self._local_summarize(text)
        elif request.action_type == AIActionType.CONTINUE_WRITING:
            modified = self._local_continue(text)
        elif request.action_type == AIActionType.GENERATE_EXAMPLES:
            modified = self._local_generate_examples(text)
        elif request.action_type == AIActionType.EXPLAIN:
            modified = self._local_explain(text)

        return AIActionResponse(
            success=True,
            action_type=request.action_type,
            original_text=text,
            modified_text=modified,
            suggestions=[],
            explanation=f"Applied {request.action_type.value} transformation",
        )

    def _build_prompt(self, request: AIActionRequest) -> str:
        prompts = {
            AIActionType.REWRITE: f"Rewrite the following text in a {request.tone} tone. {request.instructions}\n\nText: {request.text}",
            AIActionType.EXPAND: f"Expand the following text with more details and examples. {request.instructions}\n\nText: {request.text}",
            AIActionType.SIMPLIFY: f"Simplify the following text to make it easier to read. Use simpler words and shorter sentences.\n\nText: {request.text}",
            AIActionType.SHORTEN: f"Condense the following text while keeping the key information.\n\nText: {request.text}",
            AIActionType.FIX_GRAMMAR: f"Fix any grammar, spelling, and punctuation errors in the following text. Preserve the original meaning and style.\n\nText: {request.text}",
            AIActionType.IMPROVE_SEO: f"Optimize the following text for SEO while keeping it natural and readable. Include relevant keywords naturally.\n\nText: {request.text}",
            AIActionType.IMPROVE_READABILITY: f"Improve the readability of the following text. Use shorter sentences, simpler words, and better structure.\n\nText: {request.text}",
            AIActionType.IMPROVE_CLARITY: f"Improve the clarity of the following text. Make the message more direct and easier to understand.\n\nText: {request.text}",
            AIActionType.IMPROVE_TONE: f"Rewrite the following text in a {request.tone} tone.\n\nText: {request.text}",
            AIActionType.CONTINUE_WRITING: f"Continue writing from the following text. Maintain the same style and tone.\n\nText: {request.text}",
            AIActionType.SUMMARIZE: f"Summarize the following text in 2-3 sentences.\n\nText: {request.text}",
            AIActionType.GENERATE_EXAMPLES: f"Generate relevant examples for the following text.\n\nText: {request.text}",
            AIActionType.EXPLAIN: f"Explain the following text in simple terms.\n\nText: {request.text}",
        }
        return prompts.get(request.action_type, f"Process the following text: {request.text}")

    def _local_rewrite(self, text: str, tone: str, instructions: str) -> str:
        return text

    def _local_expand(self, text: str, instructions: str) -> str:
        return text + "\n\n[Additional content would be generated here by the AI provider.]"

    def _local_simplify(self, text: str) -> str:
        return text

    def _local_shorten(self, text: str) -> str:
        sentences = text.split(".")
        if len(sentences) > 3:
            return ".".join(sentences[:3]) + "."
        return text

    def _local_fix_grammar(self, text: str) -> str:
        return text

    def _local_improve_tone(self, text: str, tone: str) -> str:
        return text

    def _local_summarize(self, text: str) -> str:
        words = text.split()
        if len(words) > 100:
            return " ".join(words[:100]) + "..."
        return text

    def _local_continue(self, text: str) -> str:
        return text + "\n\n[Continuation would be generated here by the AI provider.]"

    def _local_generate_examples(self, text: str) -> str:
        return text + "\n\n**Example:** [Examples would be generated here by the AI provider.]"

    def _local_explain(self, text: str) -> str:
        return f"**Explanation:**\n\n{text}"

    def rewrite(self, text: str, tone: str = "professional", instructions: str = "") -> AIActionResponse:
        return self.execute(AIActionRequest(
            action_type=AIActionType.REWRITE,
            text=text,
            tone=tone,
            instructions=instructions,
        ))

    def expand(self, text: str, instructions: str = "") -> AIActionResponse:
        return self.execute(AIActionRequest(
            action_type=AIActionType.EXPAND,
            text=text,
            instructions=instructions,
        ))

    def simplify(self, text: str) -> AIActionResponse:
        return self.execute(AIActionRequest(
            action_type=AIActionType.SIMPLIFY,
            text=text,
        ))

    def fix_grammar(self, text: str) -> AIActionResponse:
        return self.execute(AIActionRequest(
            action_type=AIActionType.FIX_GRAMMAR,
            text=text,
        ))

    def improve_seo(self, text: str) -> AIActionResponse:
        return self.execute(AIActionRequest(
            action_type=AIActionType.IMPROVE_SEO,
            text=text,
        ))

    def summarize(self, text: str) -> AIActionResponse:
        return self.execute(AIActionRequest(
            action_type=AIActionType.SUMMARIZE,
            text=text,
        ))

    def on_change(self, callback: Callable) -> None:
        self._change_listeners.append(callback)

    def _emit(self, event: str, data: dict) -> None:
        for callback in self._change_listeners:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"AI assistant listener error: {e}")
