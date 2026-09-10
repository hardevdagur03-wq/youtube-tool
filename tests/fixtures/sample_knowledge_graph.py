from __future__ import annotations

from typing import Any


def sample_entities() -> list[dict[str, Any]]:
    return [
        {"name": "LangChain", "type": "framework", "confidence": 0.98, "mentions": [0, 16, 36, 51], "relevance": 0.95},
        {"name": "ChromaDB", "type": "database", "confidence": 0.96, "mentions": [38, 42], "relevance": 0.90},
        {"name": "OpenAI", "type": "organization", "confidence": 0.99, "mentions": [3, 5], "relevance": 0.85},
        {"name": "GPT-4o mini", "type": "model", "confidence": 0.94, "mentions": [48], "relevance": 0.80},
        {"name": "Retrieval-Augmented Generation", "type": "concept", "confidence": 0.97, "mentions": [19, 21], "relevance": 1.0},
        {"name": "Kubernetes", "type": "technology", "confidence": 0.98, "mentions": [80, 82], "relevance": 0.70},
        {"name": "Docker", "type": "technology", "confidence": 0.98, "mentions": [80], "relevance": 0.65},
        {"name": "Prometheus", "type": "technology", "confidence": 0.92, "mentions": [85], "relevance": 0.60},
        {"name": "Grafana", "type": "technology", "confidence": 0.92, "mentions": [85], "relevance": 0.55},
        {"name": "Redis", "type": "technology", "confidence": 0.95, "mentions": [83], "relevance": 0.60},
        {"name": "Semantic Chunking", "type": "technique", "confidence": 0.93, "mentions": [51, 54], "relevance": 0.88},
        {"name": "Cross-encoder", "type": "model", "confidence": 0.88, "mentions": [70], "relevance": 0.75},
    ]


def sample_relationships() -> list[dict[str, Any]]:
    return [
        {"source": "LangChain", "target": "ChromaDB", "type": "integrates_with", "weight": 0.9},
        {"source": "LangChain", "target": "OpenAI", "type": "uses", "weight": 0.85},
        {"source": "LangChain", "target": "Retrieval-Augmented Generation", "type": "implements", "weight": 0.95},
        {"source": "RAG Pipeline", "target": "Semantic Chunking", "type": "uses", "weight": 0.9},
        {"source": "RAG Pipeline", "target": "GPT-4o mini", "type": "generates_with", "weight": 0.85},
        {"source": "ChromaDB", "target": "Cosine Similarity", "type": "uses", "weight": 0.8},
        {"source": "Docker", "target": "Kubernetes", "type": "orchestrated_by", "weight": 0.9},
        {"source": "Kubernetes", "target": "RAG Pipeline", "type": "deploys", "weight": 0.85},
        {"source": "Prometheus", "target": "Grafana", "type": "data_source_for", "weight": 0.95},
        {"source": "Redis", "target": "RAG Pipeline", "type": "caches_for", "weight": 0.75},
        {"source": "OpenAI", "target": "text-embedding-3-small", "type": "provides", "weight": 0.95},
        {"source": "Query Rewriting", "target": "RAG Pipeline", "type": "optimizes", "weight": 0.85},
        {"source": "Cross-encoder", "target": "RAG Pipeline", "type": "reranks_for", "weight": 0.80},
    ]


def sample_knowledge_graph() -> dict[str, Any]:
    return {
        "entities": sample_entities(),
        "relationships": sample_relationships(),
        "facts": [
            {"statement": "RAG combines retrieval systems with generative language models.", "category": "definition", "confidence": 0.99},
            {"statement": "ChromaDB achieves sub-50ms retrieval at scale with cosine similarity.", "category": "performance", "confidence": 0.92},
            {"statement": "Semantic chunking with overlap prevents context loss at chunk boundaries.", "category": "insight", "confidence": 0.95},
            {"statement": "Query rewriting before retrieval improves hit rate by 15 percent.", "category": "statistic", "confidence": 0.88},
            {"statement": "Cross-encoder reranking adds 50ms of latency but improves relevance.", "category": "tradeoff", "confidence": 0.90},
            {"statement": "Redis caching achieves 60 percent cache hit rate for common queries.", "category": "statistic", "confidence": 0.85},
            {"statement": "End-to-end latency stays under 2 seconds for 95 percent of requests.", "category": "benchmark", "confidence": 0.90},
        ],
        "keywords": sample_keywords(),
        "pain_points": [
            {"problem": "High latency in RAG pipelines under production load", "severity": "high", "frequency": 0.85},
            {"problem": "Context loss at chunk boundaries during document splitting", "severity": "medium", "frequency": 0.75},
            {"problem": "Hallucinations from relying solely on model internal knowledge", "severity": "high", "frequency": 0.90},
            {"problem": "Difficulty scaling embedding and retrieval independently", "severity": "medium", "frequency": 0.65},
            {"problem": "Poor retrieval quality with naive text splitting", "severity": "high", "frequency": 0.80},
        ],
        "solutions": [
            {"problem": "High latency", "solution": "Implement Redis caching for embeddings and responses", "effectiveness": 0.85},
            {"problem": "Context loss", "solution": "Use semantic chunking with overlap and recursive text splitting", "effectiveness": 0.90},
            {"problem": "Hallucinations", "solution": "Ground responses in retrieved documents using RAG architecture", "effectiveness": 0.95},
            {"problem": "Scaling challenges", "solution": "Containerize with Docker and orchestrate with Kubernetes for independent scaling", "effectiveness": 0.85},
            {"problem": "Poor retrieval quality", "solution": "Implement query rewriting and cross-encoder reranking", "effectiveness": 0.88},
        ],
        "timeline": [
            {"event": "RAG concept introduced in academic literature", "timestamp": "2020", "category": "milestone"},
            {"event": "LangChain framework launched", "timestamp": "2022-10", "category": "release"},
            {"event": "ChromaDB vector database released", "timestamp": "2023-01", "category": "release"},
            {"event": "GPT-4o mini model announced", "timestamp": "2024-07", "category": "release"},
            {"event": "Production RAG adoption reaches mainstream", "timestamp": "2025", "category": "trend"},
        ],
        "statistics": [
            {"value": "0.94", "unit": "hit rate", "meaning": "Retrieval hit rate on million-document corpus", "importance": "high"},
            {"value": "0.87", "unit": "MRR", "meaning": "Mean reciprocal rank for retrieved results", "importance": "high"},
            {"value": "45", "unit": "milliseconds", "meaning": "Average retrieval time", "importance": "medium"},
            {"value": "800", "unit": "milliseconds", "meaning": "Average generation time", "importance": "medium"},
            {"value": "60", "unit": "percent", "meaning": "Redis cache hit rate for common queries", "importance": "medium"},
            {"value": "2", "unit": "seconds", "meaning": "P95 end-to-end latency target", "importance": "high"},
        ],
        "definitions": [
            {"term": "RAG", "definition": "Retrieval-Augmented Generation: technique combining document retrieval with LLM generation"},
            {"term": "Chunking", "definition": "Splitting documents into smaller pieces for embedding and retrieval"},
            {"term": "Embedding", "definition": "Vector representation of text capturing semantic meaning"},
            {"term": "Cosine Similarity", "definition": "Distance metric measuring angle between vector embeddings"},
            {"term": "MRR", "definition": "Mean Reciprocal Rank: average of reciprocal ranks of relevant retrieved documents"},
        ],
        "quotes": [
            {"text": "RAG grounds the model's responses in actual retrieved documents rather than relying solely on internal knowledge.", "speaker": "Instructor", "context": "explaining RAG benefits"},
            {"text": "The chunking strategy is critical for RAG performance.", "speaker": "Instructor", "context": "discussing implementation"},
        ],
        "semantic_clusters": [
            {
                "name": "Frameworks and Tools",
                "entities": ["LangChain", "ChromaDB", "Redis"],
                "keywords": ["pipeline", "vector store", "cache"],
                "relevance": 0.92,
            },
            {
                "name": "AI Models",
                "entities": ["OpenAI", "GPT-4o mini", "Cross-encoder", "text-embedding-3-small"],
                "keywords": ["embedding", "generation", "reranking"],
                "relevance": 0.90,
            },
            {
                "name": "Infrastructure",
                "entities": ["Kubernetes", "Docker", "Prometheus", "Grafana"],
                "keywords": ["deployment", "monitoring", "scaling"],
                "relevance": 0.85,
            },
            {
                "name": "Techniques",
                "entities": ["Semantic Chunking", "Query Rewriting", "Cosine Similarity"],
                "keywords": ["splitting", "optimization", "search"],
                "relevance": 0.88,
            },
        ],
    }


def sample_keywords() -> list[dict[str, Any]]:
    return [
        {"keyword": "RAG pipeline", "type": "primary", "score": 1.0, "volume": 42000, "difficulty": 0.65},
        {"keyword": "retrieval augmented generation", "type": "primary", "score": 0.95, "volume": 18000, "difficulty": 0.55},
        {"keyword": "LangChain tutorial", "type": "secondary", "score": 0.85, "volume": 34000, "difficulty": 0.45},
        {"keyword": "ChromaDB", "type": "secondary", "score": 0.80, "volume": 12000, "difficulty": 0.35},
        {"keyword": "vector database", "type": "secondary", "score": 0.78, "volume": 28000, "difficulty": 0.50},
        {"keyword": "semantic chunking", "type": "long_tail", "score": 0.70, "volume": 4500, "difficulty": 0.30},
        {"keyword": "production RAG deployment", "type": "long_tail", "score": 0.68, "volume": 3200, "difficulty": 0.55},
        {"keyword": "LLM embeddings", "type": "semantic", "score": 0.75, "volume": 15000, "difficulty": 0.40},
        {"keyword": "query rewriting", "type": "long_tail", "score": 0.65, "volume": 2800, "difficulty": 0.35},
        {"keyword": "cross-encoder reranking", "type": "long_tail", "score": 0.60, "volume": 1800, "difficulty": 0.40},
        {"keyword": "AI pipeline optimization", "type": "semantic", "score": 0.72, "volume": 8900, "difficulty": 0.50},
        {"keyword": "Kubernetes for AI", "type": "secondary", "score": 0.74, "volume": 11000, "difficulty": 0.55},
    ]
