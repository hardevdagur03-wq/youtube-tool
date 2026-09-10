from __future__ import annotations

import random
import time
from typing import Any


class MockTranslationAPI:
    def __init__(self) -> None:
        self._call_history: list[dict[str, Any]] = []
        self._fail_mode: str | None = None
        self._translations: dict[str, str] = {}

    def _record(self, method: str, **kwargs: Any) -> None:
        self._call_history.append({"method": method, **kwargs})

    def translate(self, text: str, target_language: str, source_language: str | None = None) -> str:
        self._record("translate", text=text, target_language=target_language, source_language=source_language)
        if self._fail_mode == "error":
            raise RuntimeError("Translation API error")
        if self._fail_mode == "timeout":
            time.sleep(5)
            raise TimeoutError("Translation API timeout")
        key = f"{text}:{target_language}"
        if key in self._translations:
            return self._translations[key]
        return f"[{target_language}] {text}"

    def detect_language(self, text: str) -> dict[str, Any]:
        self._record("detect_language", text=text)
        if self._fail_mode == "error":
            raise RuntimeError("Language detection API error")
        return {"language": "en", "confidence": 0.98, "reliable": True}

    def get_supported_languages(self) -> list[dict[str, str]]:
        self._record("get_supported_languages")
        return [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
        ]

    def register_translation(self, text: str, target_language: str, translation: str) -> None:
        self._translations[f"{text}:{target_language}"] = translation

    def simulate_error(self) -> None:
        self._fail_mode = "error"

    def simulate_timeout(self) -> None:
        self._fail_mode = "timeout"

    def reset(self) -> None:
        self._call_history.clear()
        self._fail_mode = None
        self._translations.clear()

    def record_calls(self) -> list[dict[str, Any]]:
        return list(self._call_history)


class MockOpenAIProvider:
    def __init__(self) -> None:
        self._call_history: list[dict[str, Any]] = []
        self._fail_mode: str | None = None
        self._completions: dict[str, str] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._moderation_results: list[dict[str, Any]] = []
        self._delay: float = 0.0

    def _record(self, method: str, **kwargs: Any) -> None:
        self._call_history.append({"method": method, **kwargs})

    def completion(self, prompt: str, model: str = "gpt-4o-mini", **kwargs: Any) -> dict[str, Any]:
        self._record("completion", prompt=prompt, model=model, **kwargs)
        if self._fail_mode == "error":
            raise RuntimeError("OpenAI API error")
        if self._fail_mode == "timeout":
            time.sleep(5)
            raise TimeoutError("OpenAI API timeout")
        if self._fail_mode == "rate_limit":
            raise RuntimeError("Rate limit exceeded")
        if self._delay > 0:
            time.sleep(self._delay)
        text = self._completions.get(prompt, "Mock completion response")
        return {
            "id": "mock-cmpl-001",
            "object": "text_completion",
            "created": 1700000000,
            "model": model,
            "choices": [{"text": text, "index": 0, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }

    def embedding(self, text: str, model: str = "text-embedding-3-small") -> dict[str, Any]:
        self._record("embedding", text=text, model=model)
        if self._fail_mode == "error":
            raise RuntimeError("OpenAI embedding API error")
        if text in self._embeddings:
            vector = self._embeddings[text]
        else:
            import hashlib
            h = hashlib.sha256(text.encode()).digest()
            vector = [float(b) / 255.0 for b in h[:10]] * 153
            vector = vector[:1536]
        return {
            "object": "list",
            "data": [{"object": "embedding", "embedding": vector, "index": 0}],
            "model": model,
            "usage": {"prompt_tokens": 50, "total_tokens": 50},
        }

    def moderation(self, text: str) -> dict[str, Any]:
        self._record("moderation", text=text)
        if self._fail_mode == "error":
            raise RuntimeError("OpenAI moderation API error")
        return {
            "id": "modr-001",
            "model": "text-moderation-latest",
            "results": self._moderation_results or [
                {"flagged": False, "categories": {"hate": False, "self-harm": False, "sexual": False, "violence": False}, "category_scores": {"hate": 0.001, "self-harm": 0.0001, "sexual": 0.002, "violence": 0.0005}},
            ],
        }

    def register_completion(self, prompt: str, response: str) -> None:
        self._completions[prompt] = response

    def register_embedding(self, text: str, vector: list[float]) -> None:
        self._embeddings[text] = vector

    def register_moderation_result(self, result: dict[str, Any]) -> None:
        self._moderation_results.append(result)

    def simulate_error(self) -> None:
        self._fail_mode = "error"

    def simulate_timeout(self) -> None:
        self._fail_mode = "timeout"

    def simulate_rate_limit(self) -> None:
        self._fail_mode = "rate_limit"

    def set_delay(self, seconds: float) -> None:
        self._delay = seconds

    def reset(self) -> None:
        self._call_history.clear()
        self._fail_mode = None
        self._completions.clear()
        self._embeddings.clear()
        self._moderation_results.clear()
        self._delay = 0.0

    def record_calls(self) -> list[dict[str, Any]]:
        return list(self._call_history)


class MockAnthropicProvider:
    def __init__(self) -> None:
        self._call_history: list[dict[str, Any]] = []
        self._fail_mode: str | None = None
        self._completions: dict[str, str] = {}
        self._delay: float = 0.0

    def complete(self, prompt: str, model: str = "claude-3-haiku", **kwargs: Any) -> dict[str, Any]:
        self._record("complete", prompt=prompt, model=model, **kwargs)
        if self._fail_mode == "error":
            raise RuntimeError("Anthropic API error")
        if self._fail_mode == "timeout":
            time.sleep(5)
            raise TimeoutError("Anthropic API timeout")
        if self._delay > 0:
            time.sleep(self._delay)
        text = self._completions.get(prompt, "Mock Claude response")
        return {
            "id": "mock-msg-001",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "model": model,
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }

    def register_completion(self, prompt: str, response: str) -> None:
        self._completions[prompt] = response

    def simulate_error(self) -> None:
        self._fail_mode = "error"

    def simulate_timeout(self) -> None:
        self._fail_mode = "timeout"

    def set_delay(self, seconds: float) -> None:
        self._delay = seconds

    def reset(self) -> None:
        self._call_history.clear()
        self._fail_mode = None
        self._completions.clear()
        self._delay = 0.0

    def record_calls(self) -> list[dict[str, Any]]:
        return list(self._call_history)

    def _record(self, method: str, **kwargs: Any) -> None:
        self._call_history.append({"method": method, **kwargs})


class MockGeminiProvider:
    def __init__(self) -> None:
        self._call_history: list[dict[str, Any]] = []
        self._fail_mode: str | None = None
        self._responses: dict[str, str] = {}
        self._delay: float = 0.0

    def generate_content(self, prompt: str, model: str = "gemini-2.5-flash", **kwargs: Any) -> dict[str, Any]:
        self._record("generate_content", prompt=prompt, model=model, **kwargs)
        if self._fail_mode == "error":
            raise RuntimeError("Gemini API error")
        if self._fail_mode == "timeout":
            time.sleep(5)
            raise TimeoutError("Gemini API timeout")
        if self._fail_mode == "safety":
            raise RuntimeError("Gemini safety block")
        if self._delay > 0:
            time.sleep(self._delay)
        text = self._responses.get(prompt, "Mock Gemini response")
        return {
            "candidates": [
                {
                    "content": {"parts": [{"text": text}], "role": "model"},
                    "finish_reason": "STOP",
                    "safety_ratings": [
                        {"category": "HARM_CATEGORY_HARASSMENT", "probability": "NEGLIGIBLE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "probability": "NEGLIGIBLE"},
                    ],
                }
            ],
            "usage_metadata": {"prompt_token_count": 100, "candidates_token_count": 50, "total_token_count": 150},
        }

    def register_response(self, prompt: str, response: str) -> None:
        self._responses[prompt] = response

    def simulate_error(self) -> None:
        self._fail_mode = "error"

    def simulate_timeout(self) -> None:
        self._fail_mode = "timeout"

    def simulate_safety_block(self) -> None:
        self._fail_mode = "safety"

    def set_delay(self, seconds: float) -> None:
        self._delay = seconds

    def reset(self) -> None:
        self._call_history.clear()
        self._fail_mode = None
        self._responses.clear()
        self._delay = 0.0

    def record_calls(self) -> list[dict[str, Any]]:
        return list(self._call_history)

    def _record(self, method: str, **kwargs: Any) -> None:
        self._call_history.append({"method": method, **kwargs})


class MockWhisperProvider:
    def __init__(self) -> None:
        self._call_history: list[dict[str, Any]] = []
        self._fail_mode: str | None = None
        self._transcriptions: dict[str, dict[str, Any]] = {}
        self._delay: float = 0.0

    def transcribe(self, audio_path: str, language: str | None = None, **kwargs: Any) -> dict[str, Any]:
        self._record("transcribe", audio_path=audio_path, language=language, **kwargs)
        if self._fail_mode == "error":
            raise RuntimeError("Whisper transcription error")
        if self._fail_mode == "timeout":
            time.sleep(5)
            raise TimeoutError("Whisper API timeout")
        if self._delay > 0:
            time.sleep(self._delay)
        if audio_path in self._transcriptions:
            return dict(self._transcriptions[audio_path])
        return {
            "text": "Mock transcribed text from audio file.",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Mock transcribed"},
                {"start": 2.0, "end": 4.0, "text": "text from audio"},
                {"start": 4.0, "end": 5.5, "text": "file."},
            ],
            "language": language or "en",
            "duration_seconds": 5.5,
            "processing_time_seconds": 0.5,
        }

    def register_transcription(self, audio_path: str, result: dict[str, Any]) -> None:
        self._transcriptions[audio_path] = dict(result)

    def simulate_error(self) -> None:
        self._fail_mode = "error"

    def simulate_timeout(self) -> None:
        self._fail_mode = "timeout"

    def set_delay(self, seconds: float) -> None:
        self._delay = seconds

    def reset(self) -> None:
        self._call_history.clear()
        self._fail_mode = None
        self._transcriptions.clear()
        self._delay = 0.0

    def record_calls(self) -> list[dict[str, Any]]:
        return list(self._call_history)

    def _record(self, method: str, **kwargs: Any) -> None:
        self._call_history.append({"method": method, **kwargs})
