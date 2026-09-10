from __future__ import annotations

from typing import Any


def sample_outline() -> dict[str, Any]:
    return {
        "title": {
            "primary_title": "Building a Production-Grade RAG Pipeline: Complete Guide 2025",
            "alternative_titles": [
                "RAG Pipeline Tutorial: From Zero to Production",
                "How to Build a Production RAG System with LangChain",
                "The Ultimate Guide to Retrieval-Augmented Generation",
            ],
            "seo_score": 0.88,
            "click_through_estimate": 0.072,
        },
        "headings": [
            {"level": "h1", "text": "Building a Production-Grade RAG Pipeline: Complete Guide 2025", "subsections": []},
            {"level": "h2", "text": "What is Retrieval-Augmented Generation?", "subsections": [
                {"level": "h3", "text": "Why RAG Matters for Enterprise AI", "subsections": []},
                {"level": "h3", "text": "How RAG Differs from Fine-Tuning", "subsections": []},
            ]},
            {"level": "h2", "text": "Architecture Overview: Components of a RAG Pipeline", "subsections": [
                {"level": "h3", "text": "The Ingestion Pipeline", "subsections": []},
                {"level": "h3", "text": "The Retrieval and Generation Loop", "subsections": []},
            ]},
            {"level": "h2", "text": "Choosing Your Vector Database: ChromaDB Deep Dive", "subsections": [
                {"level": "h3", "text": "ChromaDB vs Pinecone vs Weaviate", "subsections": []},
                {"level": "h3", "text": "Setting Up ChromaDB for Production", "subsections": []},
            ]},
            {"level": "h2", "text": "Semantic Chunking Strategies for Better Retrieval", "subsections": [
                {"level": "h3", "text": "Recursive Character Text Splitting", "subsections": []},
                {"level": "h3", "text": "Semantic Chunking with Overlap", "subsections": []},
                {"level": "h3", "text": "Choosing the Right Chunk Size", "subsections": []},
            ]},
            {"level": "h2", "text": "Implementing Query Rewriting for Improved Accuracy", "subsections": [
                {"level": "h3", "text": "When to Rewrite Queries", "subsections": []},
                {"level": "h3", "text": "Prompt Templates for Query Rewriting", "subsections": []},
            ]},
            {"level": "h2", "text": "Adding Cross-Encoder Reranking to Boost Relevance", "subsections": [
                {"level": "h3", "text": "Bi-Encoder vs Cross-Encoder", "subsections": []},
                {"level": "h3", "text": "Integrating Reranking into the Pipeline", "subsections": []},
            ]},
            {"level": "h2", "text": "Production Deployment with Docker and Kubernetes", "subsections": [
                {"level": "h3", "text": "Containerizing Each Component", "subsections": []},
                {"level": "h3", "text": "Kubernetes Manifests and Helm Charts", "subsections": []},
                {"level": "h3", "text": "Auto-scaling Strategies", "subsections": []},
            ]},
            {"level": "h2", "text": "Monitoring and Observability with Prometheus and Grafana", "subsections": [
                {"level": "h3", "text": "Key Metrics to Track", "subsections": []},
                {"level": "h3", "text": "Setting Up Alerts for Pipeline Degradation", "subsections": []},
            ]},
            {"level": "h2", "text": "Conclusion and Next Steps", "subsections": [
                {"level": "h3", "text": "Summary of Best Practices", "subsections": []},
                {"level": "h3", "text": "Further Reading and Resources", "subsections": []},
            ]},
        ],
        "sections": [
            {"heading": "What is Retrieval-Augmented Generation?", "type": "definition", "order": 1, "target_word_count": 350},
            {"heading": "Architecture Overview", "type": "overview", "order": 2, "target_word_count": 400},
            {"heading": "Choosing Your Vector Database", "type": "comparison", "order": 3, "target_word_count": 350},
            {"heading": "Semantic Chunking Strategies", "type": "how_to", "order": 4, "target_word_count": 450},
            {"heading": "Implementing Query Rewriting", "type": "tutorial", "order": 5, "target_word_count": 350},
            {"heading": "Cross-Encoder Reranking", "type": "tutorial", "order": 6, "target_word_count": 350},
            {"heading": "Production Deployment", "type": "guide", "order": 7, "target_word_count": 500},
            {"heading": "Monitoring and Observability", "type": "guide", "order": 8, "target_word_count": 350},
        ],
        "intro_plan": {
            "hook_approach": "problem_solution",
            "hook_text": "Your RAG pipeline is too slow. The chunks are wrong. The answers are hallucinated.",
            "reader_promise": "By the end of this guide, you'll know how to build a production-grade RAG pipeline that achieves 94 percent hit rate with sub-second latency.",
            "context": "RAG has become the standard architecture for grounding LLM responses in real data.",
            "transition": "Let's start by understanding what makes a RAG pipeline truly production-ready.",
            "target_word_count": 200,
        },
        "summary_plan": {
            "key_takeaways": [
                "RAG pipelines combine retrieval and generation for grounded, factual AI responses",
                "Semantic chunking with overlap is critical for maintaining context",
                "Query rewriting and cross-encoder reranking significantly improve retrieval quality",
                "Containerization and orchestration enable independent scaling of each component",
                "Comprehensive monitoring with Prometheus and Grafana is essential for production",
            ],
            "closing_thought": "Building a production RAG pipeline is an iterative process. Start simple, measure everything, and optimize based on real metrics.",
            "target_word_count": 150,
        },
        "cta_plan": {
            "primary_cta": {
                "text": "Subscribe for more AI engineering tutorials",
                "type": "engagement",
                "urgency": "low",
            },
            "secondary_cta": {
                "text": "Download the complete code from GitHub",
                "type": "resource",
                "urgency": "medium",
            },
            "social_cta": {
                "text": "Share this guide with your team",
                "type": "social",
                "urgency": "low",
            },
        },
        "faq_plan": [
            {"question": "What is a RAG pipeline?", "intent": "informational", "priority": 10},
            {"question": "Why use ChromaDB over other vector databases?", "intent": "comparison", "priority": 8},
            {"question": "What chunk size is best for RAG?", "intent": "technical", "priority": 7},
            {"question": "How do I deploy RAG to production?", "intent": "how_to", "priority": 9},
            {"question": "What metrics should I monitor in a RAG system?", "intent": "technical", "priority": 6},
        ],
        "word_count_estimate": {
            "total_target": 3000,
            "introduction": 200,
            "body_per_section": 350,
            "conclusion": 150,
            "faq_section": 500,
        },
        "readability_estimate": {
            "flesch_reading_ease": 52.0,
            "flesch_kincaid_grade": 10.5,
            "avg_sentence_length": 18,
            "target_audience_level": "intermediate",
        },
    }


def sample_outline_structure() -> dict[str, Any]:
    return {
        "hierarchy": {
            "h1_count": 1,
            "h2_count": 8,
            "h3_count": 15,
            "max_depth": 3,
            "is_balanced": True,
        },
        "flow": {
            "has_logical_progression": True,
            "starts_with_context": True,
            "builds_complexity": True,
            "ends_with_action": True,
        },
        "coverage": {
            "what": 0.90,
            "why": 0.85,
            "how": 0.95,
            "topics_covered": 8,
            "pain_points_addressed": 5,
        },
    }


def sample_heading_hierarchy() -> list[dict[str, Any]]:
    return [
        {"level": "h1", "text": "Building a Production-Grade RAG Pipeline", "children": [
            {"level": "h2", "text": "What is RAG?", "children": [
                {"level": "h3", "text": "Core Concepts", "children": []},
                {"level": "h3", "text": "Why RAG Matters", "children": []},
            ]},
            {"level": "h2", "text": "Architecture", "children": [
                {"level": "h3", "text": "Components", "children": []},
                {"level": "h3", "text": "Data Flow", "children": []},
            ]},
            {"level": "h2", "text": "Implementation", "children": [
                {"level": "h3", "text": "Setup", "children": []},
                {"level": "h3", "text": "Configuration", "children": []},
                {"level": "h3", "text": "Code Walkthrough", "children": []},
            ]},
        ]},
    ]
