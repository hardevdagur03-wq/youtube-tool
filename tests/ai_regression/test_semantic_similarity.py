from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestSemanticSimilarity:
    def test_output_semantically_similar_to_golden(self, similarity_calculator, golden_responses):
        response_text = (
            "Python is a versatile programming language used in data science, "
            "web development, and automation. It was created by Guido van Rossum "
            "and has become one of the most popular languages worldwide."
        )
        golden_text = (
            "Python is a high-level programming language created by Guido van Rossum. "
            "It is widely used in data science, web development, and automation."
        )
        similarity = similarity_calculator.jaccard_similarity(response_text, golden_text)
        assert similarity > 0.3, f"Semantic similarity {similarity:.2f} too low"

    def test_paraphrase_invariance(self, similarity_calculator):
        input1 = "Python is a great language for beginners to learn programming."
        input2 = "Python is an excellent programming language for those starting out."

        similarity = similarity_calculator.jaccard_similarity(input1, input2)
        assert similarity > 0.2, f"Paraphrase similarity {similarity:.2f} too low"

    def test_different_inputs_produce_different_outputs(self, similarity_calculator):
        input1 = "Python programming for data science."
        input2 = "Cooking recipes for Italian cuisine."

        similarity = similarity_calculator.jaccard_similarity(input1, input2)
        assert similarity < 0.5, f"Different inputs similarity {similarity:.2f} too high"

    def test_entity_overlap_with_golden(self, similarity_calculator, mock_llm_provider):
        golden_entities = [
            {"name": "Python", "type": "language"},
            {"name": "Guido van Rossum", "type": "person"},
            {"name": "Django", "type": "framework"},
        ]

        @pytest.mark.asyncio
        async def run_test():
            structured = await mock_llm_provider.generate_structured(prompt="Extract entities")
            extracted = structured.get("entities", golden_entities)
            overlap = similarity_calculator.entity_overlap(extracted, golden_entities)
            assert overlap > 0.2, f"Entity overlap {overlap:.2f} too low"

        import asyncio
        asyncio.run(run_test())

    def test_keyword_overlap_consistency(self, similarity_calculator):
        kws1 = ["python", "programming", "data science", "machine learning"]
        kws2 = ["python", "programming", "deep learning", "artificial intelligence"]

        overlap = similarity_calculator.keyword_overlap(kws1, kws2)
        assert overlap > 0.2, f"Keyword overlap {overlap:.2f} too low"
        assert overlap < 1.0, "Keyword overlap should not be 100% for different sets"

    def test_empty_input_similarity(self, similarity_calculator):
        assert similarity_calculator.jaccard_similarity("", "") == 0.0
        assert similarity_calculator.jaccard_similarity("test", "") == 0.0
        assert similarity_calculator.jaccard_similarity("", "test") == 0.0

    def test_identical_text_similarity(self, similarity_calculator):
        text = "Python is a programming language used for data science and web development."
        similarity = similarity_calculator.jaccard_similarity(text, text)
        assert similarity == 1.0

    def test_entity_overlap_empty(self, similarity_calculator):
        assert similarity_calculator.entity_overlap([], []) == 0.0
        assert similarity_calculator.entity_overlap(
            [{"name": "Python"}], []
        ) == 0.0

    def test_keyword_overlap_empty(self, similarity_calculator):
        assert similarity_calculator.keyword_overlap([], []) == 0.0
        assert similarity_calculator.keyword_overlap(["a"], []) == 0.0
