from __future__ import annotations

from typing import Any


def sample_seo_analysis() -> dict[str, Any]:
    return {
        "keyword_analysis": {
            "primary_keyword": "RAG Pipeline Tutorial",
            "secondary_keywords": [
                "LangChain RAG", "ChromaDB setup", "vector database tutorial",
                "production RAG deployment", "LLM retrieval augmented generation",
            ],
            "long_tail_keywords": [
                "how to build RAG pipeline LangChain",
                "production grade RAG system tutorial",
                "ChromaDB with OpenAI embeddings guide",
            ],
            "keyword_density": 0.032,
            "keyword_in_title": True,
            "keyword_in_first_paragraph": True,
            "keyword_usage_distribution": {
                "title": True,
                "h1": False,
                "h2": 3,
                "h3": 5,
                "body": 18,
                "conclusion": 2,
            },
        },
        "intent_analysis": {
            "primary_intent": "educational",
            "secondary_intents": ["informational", "how_to"],
            "intent_score": 0.92,
            "search_goal": "Learn how to build a production RAG pipeline",
            "user_stage": "consideration",
        },
        "audience_analysis": {
            "primary_audience": "Software Engineers",
            "secondary_audiences": ["ML Engineers", "Data Scientists", "DevOps Engineers"],
            "skill_level": "intermediate",
            "pain_points": [
                "RAG pipelines too slow in production",
                "Chunking strategies unclear",
                "Vector database selection confusion",
            ],
            "search_behavior": "technical tutorials and step-by-step guides",
        },
        "competitor_insights": {
            "top_competitors": [
                {"channel": "LangChain Official", "title": "RAG from Scratch", "views": 520000},
                {"channel": "AI Engineering", "title": "Build a RAG System", "views": 340000},
                {"channel": "TechWithTim", "title": "RAG Pipeline Tutorial", "views": 280000},
            ],
            "content_gaps": [
                "No comprehensive production deployment guide",
                "Lack of benchmark results with real metrics",
                "Missing monitoring and observability setup",
            ],
            "unique_angle": "Production-grade deployment with Kubernetes and monitoring",
        },
        "heading_strategy": {
            "h1": "Building a Production-Grade RAG Pipeline: Complete Guide",
            "h2_suggestions": [
                "What is Retrieval-Augmented Generation?",
                "Architecture Overview: Components of a RAG Pipeline",
                "Choosing Your Vector Database: ChromaDB Deep Dive",
                "Semantic Chunking Strategies for Better Retrieval",
                "Implementing Query Rewriting for Improved Accuracy",
                "Adding Cross-Encoder Reranking to Boost Relevance",
                "Production Deployment with Docker and Kubernetes",
                "Monitoring and Observability with Prometheus and Grafana",
            ],
            "heading_keyword_distribution": {
                "primary_in_h1": True,
                "primary_in_h2_count": 3,
                "secondary_in_h2_count": 5,
            },
        },
        "schema_markup": {
            "types": ["Article", "TechArticle", "HowTo"],
            "has_faq_schema": True,
            "has_breadcrumb": True,
            "has_video_schema": True,
        },
        "meta_tags": {
            "meta_title": "Building a Production-Grade RAG Pipeline | Complete Guide 2025",
            "meta_description": "Learn to build a production RAG pipeline with LangChain and ChromaDB. Covers semantic chunking, query rewriting, reranking, and Kubernetes deployment with monitoring.",
            "meta_keywords": "RAG pipeline, LangChain, ChromaDB, vector database, retrieval augmented generation",
            "meta_robots": "index, follow",
            "canonical_url": "https://example.com/rag-pipeline-guide",
            "og_title": "How to Build a Production RAG Pipeline from Scratch",
            "og_description": "Complete step-by-step guide covering architecture, implementation, and deployment.",
            "twitter_card": "summary_large_image",
        },
        "url_slug": "build-production-rag-pipeline-langchain-chromadb",
        "internal_links": [
            {"target": "/guides/intro-to-llms", "anchor_text": "Introduction to LLMs", "relevance": 0.85},
            {"target": "/guides/vector-databases-101", "anchor_text": "Vector Databases Explained", "relevance": 0.80},
            {"target": "/guides/langchain-basics", "anchor_text": "LangChain Fundamentals", "relevance": 0.90},
            {"target": "/guides/kubernetes-for-ml", "anchor_text": "Kubernetes for ML Workloads", "relevance": 0.70},
        ],
        "external_links": [
            {"domain": "langchain.readthedocs.io", "relevance": 0.95, "authority": 0.85},
            {"domain": "docs.trychroma.com", "relevance": 0.90, "authority": 0.75},
            {"domain": "openai.com/blog", "relevance": 0.85, "authority": 0.95},
            {"domain": "kubernetes.io/docs", "relevance": 0.70, "authority": 0.90},
        ],
        "faq_items": [
            {
                "question": "What is a RAG pipeline?",
                "answer": "A RAG pipeline combines document retrieval with generative AI to produce grounded, factual responses.",
                "priority": 10,
            },
            {
                "question": "Why use ChromaDB for RAG?",
                "answer": "ChromaDB offers sub-50ms retrieval latency, native cosine similarity, and seamless LangChain integration.",
                "priority": 8,
            },
            {
                "question": "What is semantic chunking?",
                "answer": "Semantic chunking splits documents at natural boundaries while maintaining context through overlapping segments.",
                "priority": 7,
            },
            {
                "question": "How do I deploy a RAG pipeline to production?",
                "answer": "Containerize components with Docker, orchestrate with Kubernetes, and monitor with Prometheus and Grafana.",
                "priority": 9,
            },
            {
                "question": "What is query rewriting in RAG?",
                "answer": "Query rewriting uses an LLM to reformulate user queries into more effective search queries before retrieval.",
                "priority": 6,
            },
        ],
        "featured_snippet_targets": [
            {
                "question": "How to build a RAG pipeline?",
                "target_section": "Architecture Overview",
                "current_snippet": "Combine retrieval with generation using LangChain",
                "opportunity_score": 0.85,
            },
            {
                "question": "What is the best chunking strategy for RAG?",
                "target_section": "Semantic Chunking Strategies",
                "current_snippet": "Semantic chunking with overlap outperforms naive splitting",
                "opportunity_score": 0.80,
            },
        ],
    }


def sample_seo_scores() -> dict[str, float]:
    return {
        "overall": 87.5,
        "keyword_score": 92.0,
        "readability_score": 78.5,
        "structure_score": 85.0,
        "meta_score": 95.0,
        "link_score": 82.0,
        "mobile_score": 90.0,
        "speed_score": 85.0,
    }


def sample_keyword_data() -> list[dict[str, Any]]:
    return [
        {"keyword": "RAG pipeline tutorial", "search_volume": 42000, "difficulty": 0.65, "cpc": 2.45, "competition": "medium"},
        {"keyword": "LangChain RAG", "search_volume": 28000, "difficulty": 0.55, "cpc": 1.80, "competition": "low"},
        {"keyword": "vector database", "search_volume": 35000, "difficulty": 0.50, "cpc": 3.20, "competition": "high"},
        {"keyword": "ChromaDB tutorial", "search_volume": 12000, "difficulty": 0.35, "cpc": 1.50, "competition": "low"},
        {"keyword": "production RAG", "search_volume": 8500, "difficulty": 0.60, "cpc": 4.10, "competition": "medium"},
        {"keyword": "semantic chunking", "search_volume": 4500, "difficulty": 0.30, "cpc": 2.80, "competition": "low"},
        {"keyword": "LLM retrieval augmented generation", "search_volume": 18000, "difficulty": 0.55, "cpc": 2.90, "competition": "medium"},
        {"keyword": "Kubernetes AI deployment", "search_volume": 11000, "difficulty": 0.55, "cpc": 3.50, "competition": "medium"},
    ]


def sample_seo_recommendations() -> list[dict[str, Any]]:
    return [
        {
            "type": "keyword",
            "priority": "high",
            "description": "Add primary keyword to H1 heading",
            "current": "Building a Production-Grade RAG Pipeline: Complete Guide",
            "suggestion": "RAG Pipeline Tutorial: Build Production-Grade Retrieval Augmented Generation",
            "impact": 0.15,
        },
        {
            "type": "meta",
            "priority": "medium",
            "description": "Meta description is 12 characters too long",
            "current": "Learn to build a production RAG pipeline with LangChain and ChromaDB. Covers semantic chunking, query rewriting, reranking, and deployment.",
            "suggestion": "Build a production RAG pipeline with LangChain and ChromaDB. Learn semantic chunking, query rewriting, reranking, and Kubernetes deployment.",
            "impact": 0.08,
        },
        {
            "type": "structure",
            "priority": "high",
            "description": "Add more H2 headings with secondary keywords",
            "current": "4 H2 headings",
            "suggestion": "8 H2 headings covering each major component",
            "impact": 0.12,
        },
        {
            "type": "content",
            "priority": "medium",
            "description": "Increase word count for comprehensive coverage",
            "current": 1800,
            "suggestion": 3000,
            "impact": 0.10,
        },
        {
            "type": "links",
            "priority": "low",
            "description": "Add more internal links to related tutorials",
            "current": 2,
            "suggestion": 5,
            "impact": 0.05,
        },
    ]
