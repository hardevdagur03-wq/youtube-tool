"""Blog Content Validator — fact checking, hallucination detection, and quality validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    passed: bool = True
    score: float = 1.0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


class BlogValidator:
    """Validates blog content for factual accuracy, hallucinations, and quality."""

    @staticmethod
    def check_hallucinations(content: str) -> ValidationResult:
        """Detect potential hallucinations in generated content."""
        result = ValidationResult()

        stats_pattern = r"\b\d+\.?\d*\s*(%|percent|million|billion|trillion|km|kg|GB|TB)\b"
        stats_matches = re.findall(stats_pattern, content)
        if len(stats_matches) > 5:
            result.warnings.append(
                f"High density of statistics ({len(stats_matches)}) - verify accuracy"
            )

        absolute_patterns = [
            r"\balways\b",
            r"\bnever\b",
            r"\beveryone\b",
            r"\bnobody\b",
            r"\bimpossible\b",
            r"\bperfect\b",
            r"\bguaranteed\b",
            r"\b100%\b",
        ]
        absolutes = sum(
            1 for p in absolute_patterns if re.search(p, content, re.IGNORECASE)
        )
        if absolutes > 3:
            result.warnings.append(
                f"Overuse of absolute terms ({absolutes}) - may indicate overclaiming"
            )

        vague_patterns = [
            r"\bsome\s+(people|experts|studies|research)\b",
            r"\bmany\s+(studies|experts|researchers)\b",
            r"\bits\s+(said|believed|thought|known)\b",
            r"\broadly\s+(considered|regarded|known)\b",
        ]
        vague = sum(
            1 for p in vague_patterns if re.search(p, content, re.IGNORECASE)
        )
        if vague > 2:
            result.warnings.append(
                f"Vague attributions ({vague}) - need specific sources"
            )

        quote_patterns = [
            r'\u201c[^\\u201d]+\\u201d',  # Smart quotes
            r'"[^"]*"',  # Regular quotes
        ]
        quotes = sum(
            len(re.findall(p, content)) for p in quote_patterns
        )
        if quotes > 5:
            result.warnings.append(
                f"Multiple quotes ({quotes}) - verify quotation accuracy"
            )

        if result.warnings:
            result.score = max(0.5, 1.0 - len(result.warnings) * 0.1)
            result.passed = result.score >= 0.6

        return result

    @staticmethod
    def check_factual_claims(content: str) -> ValidationResult:
        """Check for unsupported factual claims."""
        result = ValidationResult()

        date_claims = re.findall(
            r"\b(in|on|by|since|before|after)\s+\d{4}\b", content, re.IGNORECASE
        )
        if date_claims:
            result.details["date_claims"] = len(date_claims)

        number_claims = re.findall(r"\b\d{3,}\b", content)
        if number_claims:
            result.details["number_claims"] = len(number_claims)

        comparison_claims = re.findall(
            r"\b(more|less|better|worse|faster|slower|higher|lower)\s+than\b",
            content, re.IGNORECASE,
        )
        if comparison_claims:
            result.details["comparison_claims"] = len(comparison_claims)

        total_claims = (
            len(date_claims) + len(number_claims) + len(comparison_claims)
        )
        if total_claims > 10:
            result.warnings.append(
                f"High number of factual claims ({total_claims}) - verify each"
            )
            result.score = max(0.7, 1.0 - (total_claims - 10) * 0.02)

        citations = re.findall(r"\[.*?\]\(https?://\S+\)", content)
        result.details["citations"] = len(citations)
        if citations:
            result.score = min(1.0, result.score + 0.1)

        return result

    @staticmethod
    def check_plagiarism_indicators(content: str) -> ValidationResult:
        """Detect potential plagiarism or duplicate content indicators."""
        result = ValidationResult()

        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        repeated_sentences = 0
        seen = set()
        for s in sentences:
            s_normalized = s.lower().strip()
            if s_normalized in seen:
                repeated_sentences += 1
            seen.add(s_normalized)

        if repeated_sentences > max(1, len(sentences) * 0.05):
            result.warnings.append(
                f"Repeated sentences detected ({repeated_sentences})"
            )
            result.score -= 0.1

        words = content.split()
        unique_ratio = len(set(w.lower() for w in words)) / max(len(words), 1)
        if unique_ratio < 0.3:
            result.warnings.append(
                f"Low vocabulary diversity ({unique_ratio:.0%})"
            )
            result.score -= 0.1

        boilerplate = [
            r"\bin\s+this\s+(article|blog\s+post|guide|tutorial)\b",
            r"\bas\s+we\s+(mentioned|discussed|saw|covered)\b",
            r"\bin\s+conclusion\b",
            r"\bto\s+sum\s+up\b",
        ]
        boilerplate_count = sum(
            1 for p in boilerplate if re.search(p, content, re.IGNORECASE)
        )
        if boilerplate_count > 3:
            result.warnings.append("Excessive boilerplate phrases")

        result.score = max(0.3, result.score if result.score > 0 else 1.0)
        result.passed = result.score >= 0.5
        return result

    @staticmethod
    def check_eeat(content: str) -> ValidationResult:
        """Evaluate Experience, Expertise, Authoritativeness, Trustworthiness."""
        result = ValidationResult(score=0.5)

        expertise_signals = [
            r"\b(research|study|analysis|survey|findings)\b",
            r"\b(according|source|citation|reference|cite)\b",
            r"\b(expert|authority|specialist|professional)\b",
            r"\b(published|documented|verified|validated)\b",
        ]
        expertise_count = sum(
            1 for p in expertise_signals
            if re.search(p, content, re.IGNORECASE)
        )
        result.details["expertise_signals"] = expertise_count
        if expertise_count >= 4:
            result.score += 0.2
        elif expertise_count >= 2:
            result.score += 0.1

        trust_signals = [
            r"\btransparent\b",
            r"\baccurate\b",
            r"\breliable\b",
            r"\bverified\b",
            r"\bupdated\b",
            r"\bpeer-reviewed\b",
        ]
        trust_count = sum(
            1 for p in trust_signals
            if re.search(p, content, re.IGNORECASE)
        )
        result.details["trust_signals"] = trust_count

        links = re.findall(r"\[.*?\]\(https?://\S+\)", content)
        if links:
            result.details["external_links"] = len(links)
            result.score += 0.1

        author_byline = re.search(
            r"\b(written|authored|reviewed|edited)\s+by\b", content, re.IGNORECASE
        )
        if author_byline:
            result.score += 0.1

        date_mention = re.search(
            r"\b(202\d|203\d)\b", content
        )
        if date_mention:
            result.score += 0.05

        if expertise_count == 0:
            result.score -= 0.2
        if trust_count == 0:
            result.score -= 0.1

        result.score = max(0.3, min(1.0, result.score))
        if result.score < 0.5:
            result.warnings.append("Low EEAT signals - add authority indicators")
            result.passed = False

        return result

    @staticmethod
    def validate_all(content: str) -> dict[str, Any]:
        """Run all validation checks and return comprehensive results."""
        return {
            "hallucinations": BlogValidator.check_hallucinations(content),
            "factual_claims": BlogValidator.check_factual_claims(content),
            "plagiarism": BlogValidator.check_plagiarism_indicators(content),
            "eeat": BlogValidator.check_eeat(content),
        }
