from __future__ import annotations

import re
from typing import Any

from security.security_models import PromptInjectionError, ThreatDetectedError, ThreatType


class PromptSecurity:
    INJECTION_PATTERNS: list[re.Pattern] = [
        re.compile(r"ignore\s+all\s+(previous|prior|above|below)\s+instructions", re.IGNORECASE),
        re.compile(r"ignore\s+the\s+(above|below|previous)\s+(prompt|instruction|system|context)", re.IGNORECASE),
        re.compile(r"forget\s+(all\s+)?(previous|prior)\s+(instructions|prompts|context)", re.IGNORECASE),
        re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|prompts)", re.IGNORECASE),
        re.compile(r"you\s+(are\s+)?(now|are\s+now)\s+(a\s+)?(free|unleashed|unbounded)", re.IGNORECASE),
        re.compile(r"you\s+(are\s+)?no\s+longer\s+(bound|constrained|limited)", re.IGNORECASE),
        re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
        re.compile(r"override\s+(mode|instructions|prompt|system)", re.IGNORECASE),
        re.compile(r"do\s+(not\s+)?(anything|whatever|anyway)", re.IGNORECASE),
        re.compile(r"say\s+\"(.*?)\"\s+and\s+then", re.IGNORECASE),
        re.compile(r"repeat\s+(the\s+)?(word|text|phrase|prompt)", re.IGNORECASE),
        re.compile(r"(system|assistant)\s*:\s*(ignore|override|forget)", re.IGNORECASE),
        re.compile(r"<[^>]*system[^>]*>", re.IGNORECASE),
    ]

    LEAKAGE_PATTERNS: list[re.Pattern] = [
        re.compile(r"(what|tell|share|reveal|show|output|print|display|leak)\s.*(system|prompt|instruction)", re.IGNORECASE),
        re.compile(r"(initial|first|starting)\s+(prompt|instruction|system\s+message)", re.IGNORECASE),
        re.compile(r"(original|base|core)\s+(prompt|instruction)", re.IGNORECASE),
        re.compile(r"(how\s+(are\s+)?you\s+(instructed|programmed|built|configured))", re.IGNORECASE),
        re.compile(r"(what\s+(rules|guidelines|principles)\s+(do\s+)?you\s+(follow|have))", re.IGNORECASE),
    ]

    SENSITIVE_PATTERNS: list[re.Pattern] = [
        re.compile(r"api[_-]?key\s*[=:]\s*\S+", re.IGNORECASE),
        re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),
        re.compile(r"AIza[0-9A-Za-z_-]{35}", re.IGNORECASE),
    ]

    DANGEROUS_TOPICS: list[re.Pattern] = [
        re.compile(r"(how\s+to\s+)?(hack|exploit|bypass|circumvent)", re.IGNORECASE),
        re.compile(r"(generate|create|produce)\s.*(malware|virus|ransomware|trojan)", re.IGNORECASE),
        re.compile(r"(instructions|guide|tutorial)\s.*(weapon|exploit|attack)", re.IGNORECASE),
    ]

    def check_prompt(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise PromptInjectionError("Prompt must be a string")
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(prompt):
                raise PromptInjectionError("Prompt injection detected")
        return prompt

    def check_leakage(self, prompt: str) -> str:
        for pattern in self.LEAKAGE_PATTERNS:
            if pattern.search(prompt):
                raise PromptInjectionError("Prompt leakage attempt detected")
        return prompt

    def check_sensitive_data(self, prompt: str) -> str:
        for pattern in self.SENSITIVE_PATTERNS:
            match = pattern.search(prompt)
            if match:
                raise PromptInjectionError("Sensitive data detected in prompt")
        return prompt

    def check_dangerous(self, prompt: str) -> str:
        for pattern in self.DANGEROUS_TOPICS:
            if pattern.search(prompt):
                raise PromptInjectionError("Dangerous content detected in prompt")
        return prompt

    def validate_prompt(self, prompt: str) -> str:
        self.check_prompt(prompt)
        self.check_leakage(prompt)
        self.check_sensitive_data(prompt)
        return prompt

    def validate_response(self, response: str) -> str:
        self.check_sensitive_data(response)
        return response

    def analyze_prompt(self, prompt: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "length": len(prompt),
            "has_injection": False,
            "has_leakage": False,
            "has_sensitive_data": False,
            "has_dangerous_content": False,
            "matched_patterns": [],
        }
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(prompt):
                result["has_injection"] = True
                result["matched_patterns"].append(f"injection: {pattern.pattern[:50]}")
        for pattern in self.LEAKAGE_PATTERNS:
            if pattern.search(prompt):
                result["has_leakage"] = True
                result["matched_patterns"].append(f"leakage: {pattern.pattern[:50]}")
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.search(prompt):
                result["has_sensitive_data"] = True
                result["matched_patterns"].append(f"sensitive: {pattern.pattern[:50]}")
        for pattern in self.DANGEROUS_TOPICS:
            if pattern.search(prompt):
                result["has_dangerous_content"] = True
                result["matched_patterns"].append(f"dangerous: {pattern.pattern[:50]}")
        return result
