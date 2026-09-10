"""FAQ Engine — generates FAQ items from knowledge graph facts and entities.

No external API calls. No existing code is modified.
"""

from __future__ import annotations

import logging
from typing import Any

from seo_intelligence.seo_models import FAQItem

logger = logging.getLogger(__name__)


class FAQEngine:
    """Generates FAQ items from knowledge graph data."""

    def generate(
        self,
        knowledge_graph: dict[str, Any] | None,
        primary_keyword: str = "",
    ) -> list[FAQItem]:
        faqs: list[FAQItem] = []
        seen_questions: set[str] = set()
        kg = knowledge_graph or {}

        if not isinstance(kg, dict):
            return faqs

        # From facts that look like definitions
        facts = kg.get("facts", [])
        if isinstance(facts, list):
            for fact in facts:
                if isinstance(fact, dict):
                    statement = fact.get("statement", "")
                    category = fact.get("category", "")
                    if statement and len(statement) > 20:
                        question = f"What is {statement.split()[0]}?" if len(statement.split()) > 1 else ""
                        if category == "insight" or "is " in statement.lower()[:40]:
                            words = statement.split()
                            term = words[0].strip(".,;:!?")
                            if len(term) > 2:
                                question = f"What is {term}?"
                        if question and question.lower() not in seen_questions:
                            seen_questions.add(question.lower())
                            faqs.append(FAQItem(
                                question=question,
                                answer=statement[:300],
                                keyword=primary_keyword,
                                priority=7,
                                intent="informational",
                            ))

        # From definitions
        definitions = kg.get("definitions", [])
        if isinstance(definitions, list):
            for d in definitions:
                if isinstance(d, dict):
                    term = d.get("term", "")
                    definition = d.get("definition", "")
                    if term and definition:
                        question = f"What is {term}?"
                        if question.lower() not in seen_questions:
                            seen_questions.add(question.lower())
                            faqs.append(FAQItem(
                                question=question,
                                answer=definition,
                                keyword=term,
                                priority=6,
                                intent="informational",
                            ))

        # Generic questions about primary keyword
        if primary_keyword:
            generic_questions = [
                f"What is {primary_keyword}?",
                f"Why is {primary_keyword} important?",
                f"How does {primary_keyword} work?",
                f"What are the benefits of {primary_keyword}?",
            ]
            for question in generic_questions:
                if question.lower() not in seen_questions:
                    seen_questions.add(question.lower())
                    faqs.append(FAQItem(
                        question=question,
                        answer="",
                        keyword=primary_keyword,
                        priority=5,
                        intent="informational",
                    ))

        return faqs
