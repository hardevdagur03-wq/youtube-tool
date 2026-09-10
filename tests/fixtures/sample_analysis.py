from __future__ import annotations

from typing import Any


def sample_content_analysis() -> dict[str, Any]:
    return {
        "primary_topic": "Building Production RAG Pipelines with LangChain",
        "secondary_topics": [
            "Vector Databases and Embeddings",
            "Query Optimization and Reranking",
            "Production Deployments with Kubernetes",
            "Monitoring and Observability for AI Systems",
        ],
        "key_points": [
            "RAG combines retrieval systems with generative AI for grounded responses",
            "Semantic chunking with overlap significantly improves retrieval quality",
            "ChromaDB with cosine similarity provides sub-50ms retrieval at scale",
            "Query rewriting before retrieval boosts hit rate by 15 percent",
            "Containerization with Docker and Kubernetes enables independent scaling",
        ],
        "sentiment": {
            "overall": "positive",
            "score": 0.78,
            "magnitude": 0.65,
            "per_segment": [
                {"segment": "introduction", "sentiment": "neutral", "score": 0.1},
                {"segment": "explanation", "sentiment": "positive", "score": 0.7},
                {"segment": "architecture", "sentiment": "positive", "score": 0.8},
                {"segment": "implementation", "sentiment": "positive", "score": 0.9},
                {"segment": "conclusion", "sentiment": "positive", "score": 0.6},
            ],
        },
        "complexity": {
            "overall": 0.72,
            "vocabulary": 0.68,
            "sentence_structure": 0.75,
            "concept_density": 0.82,
            "technical_depth": 0.85,
        },
        "target_audience": {
            "primary": "Software Engineers",
            "secondary": ["Data Scientists", "ML Engineers", "DevOps Engineers"],
            "experience_level": "intermediate",
            "prerequisites": ["Python experience", "Basic LLM knowledge"],
        },
        "content_type": "tutorial",
        "tone": "conversational",
        "structure": {
            "type": "step_by_step",
            "has_introduction": True,
            "has_conclusion": True,
            "has_code_examples": True,
            "has_visual_aids": False,
            "section_count": 6,
        },
        "entities": [
            {"name": "LangChain", "type": "framework", "relevance": 0.95},
            {"name": "ChromaDB", "type": "technology", "relevance": 0.90},
            {"name": "OpenAI", "type": "company", "relevance": 0.85},
            {"name": "GPT-4o mini", "type": "model", "relevance": 0.80},
            {"name": "Kubernetes", "type": "technology", "relevance": 0.70},
            {"name": "Docker", "type": "technology", "relevance": 0.65},
            {"name": "Prometheus", "type": "technology", "relevance": 0.60},
            {"name": "Grafana", "type": "technology", "relevance": 0.55},
            {"name": "Redis", "type": "technology", "relevance": 0.50},
        ],
        "themes": [
            "Software Architecture and Design",
            "AI and Machine Learning",
            "DevOps and Infrastructure",
            "Performance Optimization",
        ],
        "summary": (
            "This tutorial covers building a production-grade RAG pipeline using LangChain, "
            "ChromaDB, and OpenAI embeddings. The instructor walks through semantic chunking "
            "strategies, vector indexing, query rewriting, and reranking. The video concludes "
            "with deployment best practices using Docker and Kubernetes, plus monitoring "
            "setup with Prometheus and Grafana. Benchmark results show 94% hit rate with "
            "sub-50ms retrieval latency on a million-document corpus."
        ),
        "key_insights": [
            "Semantic chunking with 64-token overlap prevents context loss at boundaries",
            "Query rewriting before retrieval improves hit rate by 15 percentage points",
            "Cross-encoder reranking adds 50ms but significantly boosts result relevance",
            "Redis caching achieves 60% hit rate for common queries in production",
            "End-to-end latency stays under 2 seconds for 95% of requests when optimized",
        ],
    }


def sample_analysis_result() -> dict[str, Any]:
    return {
        "success": True,
        "project_uuid": "proj-rag-001",
        "video_id": "dQw4w9WgXcQ",
        "analysis": sample_content_analysis(),
        "execution_time_ms": 12450,
        "model_used": "gpt-4o-mini",
        "tokens_used": 4520,
    }


def sample_analysis_metrics() -> dict[str, float]:
    return {
        "relevance": 0.92,
        "coherence": 0.88,
        "completeness": 0.85,
        "novelty": 0.72,
        "actionability": 0.80,
        "accuracy": 0.95,
        "consistency": 0.90,
        "coverage": 0.78,
        "depth": 0.82,
        "overall": 0.85,
    }
