from __future__ import annotations

from typing import Any


def sample_optimization_result() -> dict[str, Any]:
    return {
        "applied_changes": [
            {
                "type": "seo",
                "section": "introduction",
                "description": "Added primary keyword to the first paragraph",
                "before": "RAG is an AI architecture that combines document retrieval with generation.",
                "after": "RAG pipeline implementation combines document retrieval with generative language models for grounded AI responses.",
                "impact": 0.08,
            },
            {
                "type": "readability",
                "section": "body_architecture",
                "description": "Split three long sentences into shorter ones",
                "before": "A production RAG pipeline consists of several components that work together to index, retrieve, and generate responses, and understanding each component is essential for building a system that performs well at scale.",
                "after": "A production RAG pipeline consists of several components that work together. They index, retrieve, and generate responses. Understanding each component is essential for building a system that performs well at scale.",
                "impact": 0.05,
            },
            {
                "type": "passive_voice",
                "section": "body_chunking",
                "description": "Converted passive voice to active voice",
                "before": "The chunking strategy is configured by the developer based on document type.",
                "after": "Developers configure the chunking strategy based on document type.",
                "impact": 0.02,
            },
            {
                "type": "seo",
                "section": "conclusion",
                "description": "Added primary keyword to conclusion paragraph",
                "before": "Building a production system requires careful attention to each component.",
                "after": "Building a production RAG pipeline requires careful attention to each component of the retrieval augmented generation system.",
                "impact": 0.06,
            },
            {
                "type": "readability",
                "section": "monitoring",
                "description": "Added subheadings to break up long text block",
                "before": "### Monitoring and Observability\n\nProduction RAG pipelines require comprehensive monitoring...",
                "after": "### Monitoring and Observability\n\n#### Key Metrics to Track\n\nProduction RAG pipelines require comprehensive monitoring...\n\n#### Setting Up Alerts\n\nSet up alerts for critical threshold violations...",
                "impact": 0.04,
            },
        ],
        "score_improvements": {
            "overall": 7.5,
            "seo": 8.0,
            "readability": 6.0,
            "grammar": 2.0,
            "passive_voice": 3.0,
            "structure": 5.0,
        },
        "original_scores": {
            "overall": 79.0,
            "seo": 80.0,
            "readability": 72.0,
            "grammar": 93.0,
            "passive_voice": 82.0,
            "structure": 78.0,
        },
        "optimized_scores": {
            "overall": 86.5,
            "seo": 88.0,
            "readability": 78.0,
            "grammar": 95.0,
            "passive_voice": 85.0,
            "structure": 83.0,
        },
        "optimized_content": (
            "# Building a Production-Grade RAG Pipeline: Complete Guide 2025\n\n"
            "## Introduction\n\n"
            "Your RAG pipeline is too slow. The chunks are wrong. The answers are "
            "hallucinated. Building a production RAG pipeline implementation requires "
            "careful consideration of each component. This guide will walk you through "
            "building a retrieval augmented generation system that achieves 94 percent "
            "hit rate with sub-second latency.\n\n"
            "## What is Retrieval-Augmented Generation?\n\n"
            "RAG is an AI architecture that combines document retrieval with generative "
            "language models. Instead of relying solely on the model's internal knowledge, "
            "RAG first retrieves relevant documents from a knowledge base and uses them "
            "as context for generation. This dramatically reduces hallucinations and "
            "improves factual accuracy.\n\n"
            "## Semantic Chunking Strategies\n\n"
            "Developers configure the chunking strategy based on document type. The "
            "RecursiveCharacterTextSplitter from LangChain uses a hierarchy of "
            "separators to split documents. It first tries double newlines, then single "
            "newlines, then periods, and finally characters.\n\n"
            "## Conclusion\n\n"
            "Building a production RAG pipeline requires careful attention to each "
            "component of the retrieval augmented generation system. Start with a simple "
            "implementation, measure everything, and optimize based on real metrics."
        ),
    }


def sample_optimization_plan() -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "type": "seo",
            "priority": "high",
            "description": "Add primary keyword to introduction paragraph",
            "estimated_impact": 0.08,
            "difficulty": "easy",
        },
        {
            "step": 2,
            "type": "seo",
            "priority": "high",
            "description": "Add primary keyword to conclusion section",
            "estimated_impact": 0.06,
            "difficulty": "easy",
        },
        {
            "step": 3,
            "type": "readability",
            "priority": "high",
            "description": "Split long sentences in architecture section",
            "estimated_impact": 0.05,
            "difficulty": "easy",
        },
        {
            "step": 4,
            "type": "readability",
            "priority": "medium",
            "description": "Add subheadings to monitoring section",
            "estimated_impact": 0.04,
            "difficulty": "medium",
        },
        {
            "step": 5,
            "type": "passive_voice",
            "priority": "medium",
            "description": "Convert passive voice to active throughout",
            "estimated_impact": 0.03,
            "difficulty": "medium",
        },
        {
            "step": 6,
            "type": "content",
            "priority": "medium",
            "description": "Add FAQ section with common RAG questions",
            "estimated_impact": 0.07,
            "difficulty": "hard",
        },
        {
            "step": 7,
            "type": "structure",
            "priority": "low",
            "description": "Add comparison table for vector databases",
            "estimated_impact": 0.05,
            "difficulty": "medium",
        },
        {
            "step": 8,
            "type": "accessibility",
            "priority": "low",
            "description": "Add alt text descriptions to code examples",
            "estimated_impact": 0.02,
            "difficulty": "easy",
        },
    ]


def sample_optimization_changes() -> list[dict[str, Any]]:
    return [
        {
            "type": "seo",
            "section": "introduction",
            "before_text": "RAG is an AI architecture that combines document retrieval with generation.",
            "after_text": "Building a production RAG pipeline implementation combines document retrieval with generative language models for grounded AI responses.",
            "impact": 0.08,
            "characters_changed": 48,
        },
        {
            "type": "readability",
            "section": "architecture",
            "before_text": "A production RAG pipeline consists of several components that work together to index, retrieve, and generate responses, and understanding each component is essential.",
            "after_text": "A production RAG pipeline consists of several components that work together. They index, retrieve, and generate responses. Understanding each component is essential.",
            "impact": 0.05,
            "characters_changed": 35,
        },
        {
            "type": "passive_voice",
            "section": "chunking",
            "before_text": "The chunking strategy is configured by the developer based on document type.",
            "after_text": "Developers configure the chunking strategy based on document type.",
            "impact": 0.02,
            "characters_changed": 12,
        },
        {
            "type": "readability",
            "section": "monitoring",
            "before_text": "Production RAG pipelines require comprehensive monitoring to ensure reliability and performance across all components.",
            "after_text": "### Key Metrics to Track\n\nProduction RAG pipelines require comprehensive monitoring to ensure reliability and performance.",
            "impact": 0.04,
            "characters_changed": 28,
        },
    ]
