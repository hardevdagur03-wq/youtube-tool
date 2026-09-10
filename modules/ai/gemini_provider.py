"""Gemini provider — default for Phase 7 blog generation."""

from __future__ import annotations
import json
import logging
import time
from typing import Any

from modules.ai.provider import LLMProvider, LLMResponse, ProviderConfig
from exceptions.analysis_errors import (
    LLMProviderError, LLMAuthenticationError, LLMRateLimitError,
    LLMContextLengthError, LLMTimeoutError,
)

logger = logging.getLogger(__name__)

_MODEL_COST_PER_1K = {
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash": {"input": 0.000075, "output": 0.0003},
}


def _estimate_cost(model: str, inp: int, out: int) -> float:
    rates = _MODEL_COST_PER_1K.get(model.lower(), {"input": 0.00125, "output": 0.005})
    return round((inp / 1000) * rates["input"] + (out / 1000) * rates["output"], 6)


class GeminiProvider(LLMProvider):

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config)
        if not self.config.api_key:
            raise LLMAuthenticationError("Gemini API key required.")
        if not self.config.model:
            self.config.model = "gemini-2.5-flash"
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self.config.model

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai as _genai
                self._client = _genai.Client(api_key=self.config.api_key)
            except ImportError:
                raise LLMProviderError("pip install google-genai")
        return self._client

    def _call(self, prompt: str, system_prompt: str | None, json_mode: bool) -> Any:
        client = self._get_client()
        contents = [system_prompt, prompt] if system_prompt else [prompt]
        config: dict[str, Any] = {
            "temperature": self.config.temperature,
            "max_output_tokens": self.config.max_output_tokens,
        }
        if json_mode:
            config["response_mime_type"] = "application/json"
        try:
            return client.models.generate_content(model=self.config.model, contents=contents, config=config)
        except Exception as exc:
            raise self._map_error(exc)

    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        start = time.time()
        resp = self._call(prompt, system_prompt, json_mode=False)
        elapsed = (time.time() - start) * 1000
        text = resp.text or ""
        usage = getattr(resp, "usage_metadata", None)
        inp = usage.prompt_token_count if usage else 0
        out = usage.candidates_token_count if usage else 0
        return LLMResponse(
            text=text, provider=self.provider_name, model=self.config.model,
            input_tokens=inp, output_tokens=out, total_tokens=inp + out,
            latency_ms=round(elapsed, 1),
            cost_estimate=_estimate_cost(self.config.model, inp, out),
        )

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        start = time.time()
        resp = self._call(prompt, system_prompt, json_mode=True)
        elapsed = (time.time() - start) * 1000
        text = (resp.text or "{}").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"raw": text}
        usage = getattr(resp, "usage_metadata", None)
        inp = usage.prompt_token_count if usage else 0
        out = usage.candidates_token_count if usage else 0
        logger.info("gemini/%s: %d in %d out %.1fms $%.6f", self.config.model, inp, out, elapsed, _estimate_cost(self.config.model, inp, out))
        return data

    @staticmethod
    def _map_error(exc: Exception) -> LLMProviderError:
        msg = str(exc).lower()
        if "api key" in msg or "permission" in msg or "not found" in msg:
            return LLMAuthenticationError(str(exc))
        if "rate" in msg or "quota" in msg or "429" in msg:
            return LLMRateLimitError(str(exc))
        if "maximum" in msg or "length" in msg or "too long" in msg:
            return LLMContextLengthError(str(exc))
        if "timeout" in msg or "deadline" in msg:
            return LLMTimeoutError(str(exc))
        return LLMProviderError(str(exc))
