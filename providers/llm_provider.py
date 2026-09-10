"""Abstract LLM provider interface with interchangeable backends."""

from __future__ import annotations
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from exceptions.analysis_errors import (
    LLMProviderError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMContextLengthError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    cost_estimate: float = 0.0


@dataclass
class ProviderConfig:
    api_key: str = ""
    model: str = ""
    temperature: float = 0.1
    max_tokens: int = 4096
    timeout: int = 60
    max_retries: int = 3
    base_url: str | None = None
    organization: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


_MODEL_COST_PER_1K = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.005},
    "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash": {"input": 0.000075, "output": 0.0003},
    "llama-3.1-70b": {"input": 0.00059, "output": 0.00079},
    "llama-3.1-8b": {"input": 0.0001, "output": 0.0001},
    "mistral-large": {"input": 0.002, "output": 0.006},
    "mistral-small": {"input": 0.0002, "output": 0.0006},
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = _MODEL_COST_PER_1K.get(model.lower(), {"input": 0.002, "output": 0.008})
    input_cost = (input_tokens / 1000) * rates["input"]
    output_cost = (output_tokens / 1000) * rates["output"]
    return round(input_cost + output_cost, 6)


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        self.config = config or ProviderConfig()
        self._request_id: str = ""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        ...

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    def _new_request_id(self) -> str:
        self._request_id = uuid.uuid4().hex[:8]
        return self._request_id

    def _log_request(self, prompt: str, response: LLMResponse) -> None:
        logger.info(
            "[%s] %s/%s: %d in → %d out (%d total) | %.1fms | $%.6f",
            self._request_id,
            self.provider_name,
            self.model_name,
            response.input_tokens,
            response.output_tokens,
            response.total_tokens,
            response.latency_ms,
            response.cost_estimate,
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config)
        if not self.config.api_key:
            raise LLMAuthenticationError("OpenAI API key is required.")
        if not self.config.model:
            self.config.model = "gpt-4o-mini"
        self._client: Any = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.config.model

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI as _OpenAI
                kwargs: dict[str, Any] = {"api_key": self.config.api_key}
                if self.config.base_url:
                    kwargs["base_url"] = self.config.base_url
                if self.config.organization:
                    kwargs["organization"] = self.config.organization
                self._client = _OpenAI(**kwargs)
            except ImportError:
                raise LLMProviderError("openai package not installed. Run: pip install openai")
        return self._client

    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        self._new_request_id()
        start = time.time()
        client = self._get_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
            )
        except Exception as exc:
            raise self._map_error(exc)

        elapsed = (time.time() - start) * 1000
        choice = resp.choices[0]
        result = LLMResponse(
            text=choice.message.content or "",
            model=self.config.model,
            provider=self.provider_name,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=round(elapsed, 1),
            cost_estimate=estimate_cost(
                self.config.model,
                resp.usage.prompt_tokens if resp.usage else 0,
                resp.usage.completion_tokens if resp.usage else 0,
            ),
        )
        self._log_request(prompt, result)
        return result

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        self._new_request_id()
        start = time.time()
        client = self._get_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise self._map_error(exc)

        elapsed = (time.time() - start) * 1000
        choice = resp.choices[0]
        import json
        text = choice.message.content or "{}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"raw": text}

        result = LLMResponse(
            text=text,
            model=self.config.model,
            provider=self.provider_name,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            total_tokens=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=round(elapsed, 1),
            cost_estimate=estimate_cost(
                self.config.model,
                resp.usage.prompt_tokens if resp.usage else 0,
                resp.usage.completion_tokens if resp.usage else 0,
            ),
        )
        self._log_request(prompt, result)
        return data

    @staticmethod
    def _map_error(exc: Exception) -> LLMProviderError:
        msg = str(exc).lower()
        if "authentication" in msg or "api key" in msg:
            return LLMAuthenticationError(str(exc))
        if "rate limit" in msg or "429" in msg:
            return LLMRateLimitError(str(exc))
        if "context length" in msg or "maximum context" in msg or "token" in msg:
            return LLMContextLengthError(str(exc))
        if "timeout" in msg:
            return LLMTimeoutError(str(exc))
        return LLMProviderError(str(exc))


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config)
        if not self.config.api_key:
            raise LLMAuthenticationError("Anthropic API key is required.")
        if not self.config.model:
            self.config.model = "claude-3-haiku"

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self.config.model

    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise LLMProviderError("anthropic package not installed. Run: pip install anthropic")

        self._new_request_id()
        start = time.time()
        client = Anthropic(api_key=self.config.api_key)
        kwargs: dict[str, Any] = dict(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            resp = client.messages.create(**kwargs)
        except Exception as exc:
            raise self._map_error(exc)

        elapsed = (time.time() - start) * 1000
        result = LLMResponse(
            text=resp.content[0].text,
            model=self.config.model,
            provider=self.provider_name,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
            latency_ms=round(elapsed, 1),
            cost_estimate=estimate_cost(self.config.model, resp.usage.input_tokens, resp.usage.output_tokens),
        )
        self._log_request(prompt, result)
        return result

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        import json
        resp = self.generate(prompt, system_prompt)
        try:
            return json.loads(resp.text)
        except json.JSONDecodeError:
            return {"raw": resp.text}

    @staticmethod
    def _map_error(exc: Exception) -> LLMProviderError:
        msg = str(exc).lower()
        if "authentication" in msg or "api key" in msg:
            return LLMAuthenticationError(str(exc))
        if "rate" in msg:
            return LLMRateLimitError(str(exc))
        if "too large" in msg or "context" in msg:
            return LLMContextLengthError(str(exc))
        if "timeout" in msg:
            return LLMTimeoutError(str(exc))
        return LLMProviderError(str(exc))


class GeminiProvider(LLMProvider):
    """Google Gemini provider using google.genai (v2+ API)."""

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config)
        if not self.config.api_key:
            raise LLMAuthenticationError("Gemini API key is required.")
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
                raise LLMProviderError("google-genai not installed. Run: pip install google-genai")
        return self._client

    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        self._new_request_id()
        start = time.time()
        client = self._get_client()
        contents = [system_prompt, prompt] if system_prompt else [prompt]

        try:
            resp = client.models.generate_content(
                model=self.config.model,
                contents=contents,
                config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                },
            )
        except Exception as exc:
            raise self._map_error(exc)

        elapsed = (time.time() - start) * 1000
        text = resp.text or ""

        usage = None
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            usage = resp.usage_metadata

        return LLMResponse(
            text=text,
            model=self.config.model,
            provider=self.provider_name,
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            total_tokens=(usage.prompt_token_count + usage.candidates_token_count) if usage else 0,
            latency_ms=round(elapsed, 1),
            cost_estimate=estimate_cost(self.config.model, usage.prompt_token_count if usage else 0, usage.candidates_token_count if usage else 0),
        )

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        self._new_request_id()
        start = time.time()
        client = self._get_client()
        contents = [system_prompt, prompt] if system_prompt else [prompt]

        try:
            resp = client.models.generate_content(
                model=self.config.model,
                contents=contents,
                config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                    "response_mime_type": "application/json",
                },
            )
        except Exception as exc:
            raise self._map_error(exc)

        elapsed = (time.time() - start) * 1000
        text = resp.text or "{}"
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"raw": text}

        usage = None
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            usage = resp.usage_metadata

        result = LLMResponse(
            text=text,
            model=self.config.model,
            provider=self.provider_name,
            input_tokens=usage.prompt_token_count if usage else 0,
            output_tokens=usage.candidates_token_count if usage else 0,
            total_tokens=(usage.prompt_token_count + usage.candidates_token_count) if usage else 0,
            latency_ms=round(elapsed, 1),
            cost_estimate=estimate_cost(self.config.model, usage.prompt_token_count if usage else 0, usage.candidates_token_count if usage else 0),
        )
        self._log_request(prompt, result)
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


class MockProvider(LLMProvider):
    """Deterministic mock provider for testing and fallback.

    Uses keyword matching to produce plausible structured output
    without calling any external API.
    """

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config)
        self.config.model = self.config.model or "mock-v1"

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return self.config.model

    def generate(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        self._new_request_id()
        start = time.time()
        text = self._mock_response(prompt)
        elapsed = (time.time() - start) * 1000
        return LLMResponse(
            text=text,
            model=self.model_name,
            provider=self.provider_name,
            input_tokens=len(prompt.split()),
            output_tokens=len(text.split()),
            total_tokens=len(prompt.split()) + len(text.split()),
            latency_ms=round(elapsed, 1),
            cost_estimate=0.0,
        )

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        import json
        resp = self.generate(prompt, system_prompt)
        try:
            return json.loads(resp.text)
        except json.JSONDecodeError:
            return {"mock": True, "note": "Mock provider falls back to keyword analysis"}

    def _mock_response(self, prompt: str) -> str:
        transcript_text = prompt[:2000].lower()

        topics = self._extract_topics(transcript_text)
        primary_topic = topics[0] if topics else "Unknown Topic"

        return json.dumps({
            "primary_topic": primary_topic,
            "secondary_topics": topics[1:5],
            "category": self._classify_category(transcript_text),
            "subcategory": "",
            "content_type": "tutorial",
            "search_intent": "informational",
            "intent_confidence": 0.85,
            "target_audience": "General audience interested in technology",
            "experience_level": "beginner",
            "industry": "Technology",
            "difficulty": "beginner",
            "content_purpose": "Educate the audience about " + primary_topic,
            "problem_statement": "Understanding " + primary_topic,
            "main_solution": "A comprehensive overview of " + primary_topic,
            "key_takeaways": ["Learn about " + primary_topic],
            "pain_points": [],
            "opportunities": [],
            "action_items": ["Review the concepts presented in this video"],
            "call_to_actions": [],
            "learning_objectives": ["Understand " + primary_topic],
            "business_value": "",
            "educational_value": "Educational overview of " + primary_topic,
            "summary": {
                "short": f"This video covers {primary_topic}.",
                "executive": f"The video provides an overview of {primary_topic}.",
                "detailed": f"This video discusses {primary_topic} in detail.",
                "bullet_points": [f"Introduction to {primary_topic}"],
                "key_insights": [],
                "main_arguments": [],
                "important_facts": [],
                "actionable_points": [],
            },
            "keywords": {
                "primary": primary_topic,
                "secondary": topics[1:5],
                "long_tail": [f"learn {primary_topic}"],
                "semantic": [],
                "lsi": [],
                "related_topics": topics[1:5],
                "trending_terms": [],
                "brand_names": [],
                "products": [],
                "technologies": [],
                "frameworks": [],
            },
            "entities": {
                "people": [],
                "companies": [],
                "organizations": [],
                "universities": [],
                "countries": [],
                "cities": [],
                "technologies": [],
                "programming_languages": [],
                "frameworks": [],
                "books": [],
                "courses": [],
                "tools": [],
                "products": [],
                "standards": [],
                "government_agencies": [],
                "dates": [],
                "statistics": [],
            },
            "outline": {
                "sections": [
                    f"Introduction to {primary_topic}",
                    "Background and Context",
                    "Core Concepts",
                    "Key Takeaways",
                    "Conclusion",
                ],
                "introduction": f"This video introduces {primary_topic}.",
                "main_body": ["Core concepts of " + primary_topic],
                "conclusion": f"Summary of {primary_topic}.",
            },
            "quality": {
                "topic_coverage": 70.0,
                "depth_score": 60.0,
                "readability": 80.0,
                "information_density": 60.0,
                "technical_complexity": 40.0,
                "educational_value": 70.0,
                "uniqueness": 50.0,
                "seo_potential": 65.0,
                "evergreen_score": 60.0,
                "engagement_potential": 65.0,
                "confidence": 0.60,
            },
        })

    @staticmethod
    def _extract_topics(text: str) -> list[str]:
        from utils.text_utils import count_words
        words = [w for w in text.split() if len(w) > 3]
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq, key=freq.get, reverse=True)
        return sorted_words[:10]

    @staticmethod
    def _classify_category(text: str) -> str:
        categories = {
            "programming": ["python", "javascript", "code", "software", "api", "algorithm"],
            "ai": ["machine learning", "deep learning", "neural", "gpt", "llm", "ai"],
            "technology": ["computer", "internet", "web", "digital", "tech", "software"],
            "education": ["learn", "study", "course", "tutorial", "lesson", "teach"],
            "business": ["business", "startup", "entrepreneur", "marketing", "revenue"],
            "science": ["science", "research", "study", "experiment", "data", "analysis"],
            "finance": ["money", "invest", "stock", "finance", "economy", "budget"],
            "healthcare": ["health", "medical", "doctor", "disease", "treatment", "patient"],
        }
        for cat, keywords in categories.items():
            for kw in keywords:
                if kw in text:
                    return cat
        return "technology"


def create_provider(config: ProviderConfig) -> LLMProvider:
    """Factory: create the appropriate LLM provider based on config."""
    api_key = config.api_key or ""

    if config.extra.get("provider") == "gemini" or (
        api_key and not api_key.startswith("sk-") and not api_key.startswith("sk-ant-")
    ):
        return GeminiProvider(config)
    if api_key.startswith("sk-ant-"):
        return AnthropicProvider(config)
    if api_key.startswith("sk-"):
        return OpenAIProvider(config)
    logger.info("No valid LLM API key found — using MockProvider for analysis.")
    return MockProvider(config)
