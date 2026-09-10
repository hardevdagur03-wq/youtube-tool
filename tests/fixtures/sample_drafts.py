from __future__ import annotations

from typing import Any


def sample_draft() -> dict[str, Any]:
    return {
        "title": "Building a Production-Grade RAG Pipeline: Complete Guide 2025",
        "content": (
            "# Building a Production-Grade RAG Pipeline: Complete Guide 2025\n\n"
            "## Introduction\n\n"
            "Your RAG pipeline is too slow. The chunks are wrong. The answers are "
            "hallucinated. If you have tried to deploy a production RAG system, you "
            "have likely faced these challenges. This guide will walk you through "
            "building a RAG pipeline that achieves 94 percent hit rate with "
            "sub-second latency.\n\n"
            "## What is Retrieval-Augmented Generation?\n\n"
            "RAG is an AI architecture that combines document retrieval with generative "
            "language models. Instead of relying solely on the model's internal knowledge, "
            "RAG first retrieves relevant documents from a knowledge base and uses them "
            "as context for generation. This dramatically reduces hallucinations.\n\n"
            "### Why RAG Matters for Enterprise AI\n\n"
            "Enterprise AI systems need to answer questions based on specific, often "
            "private, knowledge bases. Fine-tuning cannot keep up with rapidly changing "
            "information. RAG provides a way to ground AI responses in the most current "
            "data without retraining the model.\n\n"
            "### How RAG Differs from Fine-Tuning\n\n"
            "Fine-tuning modifies the model weights to incorporate new knowledge. This "
            "is expensive, slow, and makes the model less flexible. RAG keeps the model "
            "frozen and provides relevant context at query time. This makes it cheaper, "
            "faster to update, and more transparent.\n\n"
            "## Architecture Overview: Components of a RAG Pipeline\n\n"
            "A production RAG pipeline consists of several components that work together "
            "to index, retrieve, and generate responses. Understanding each component "
            "is essential for building a system that performs well at scale.\n\n"
            "### The Ingestion Pipeline\n\n"
            "The ingestion pipeline processes documents and stores them in a vector "
            "database. It includes document parsing, chunking, embedding, and indexing. "
            "Each step must be carefully configured for the specific type of content "
            "being processed.\n\n"
            "### The Retrieval and Generation Loop\n\n"
            "At query time, the pipeline embeds the user's question, retrieves relevant "
            "chunks from the vector database, optionally reranks them, and passes them "
            "as context to the LLM for generation. This loop typically completes in "
            "under one second in well-optimized systems.\n\n"
            "## Semantic Chunking Strategies\n\n"
            "Chunking is the most critical preprocessing step. Poor chunking produces "
            "poor results regardless of other optimizations. Semantic chunking respects "
            "natural language boundaries rather than cutting at arbitrary token counts.\n\n"
            "### Recursive Character Text Splitting\n\n"
            "The RecursiveCharacterTextSplitter from LangChain uses a hierarchy of "
            "separators to split documents. It first tries double newlines, then single "
            "newlines, then periods, and finally characters. This ensures chunks respect "
            "natural document structure.\n\n"
            "### Chunk Overlap Configuration\n\n"
            "A standard configuration uses 512 token chunks with 64 tokens of overlap. "
            "This prevents context loss at chunk boundaries while maintaining efficient "
            "storage and retrieval. The overlap ensures that information near boundaries "
            "appears in at least two chunks.\n\n"
            "## Query Rewriting for Improved Accuracy\n\n"
            "Query rewriting uses an LLM to transform user questions into more effective "
            "search queries. This resolves ambiguity, incorporates conversation history, "
            "and matches document vocabulary. Our benchmarks show a 15 percent "
            "improvement in hit rate with this technique.\n\n"
            "## Cross-Encoder Reranking\n\n"
            "After initial retrieval, a cross-encoder model reranks the results by "
            "evaluating the relevance of each chunk against the query. This adds 50 "
            "milliseconds of latency but significantly improves the quality of top "
            "results. The cross-encoder considers the full interaction between query "
            "and document, unlike bi-encoders which encode them separately.\n\n"
            "## Production Deployment\n\n"
            "Containerize each component with Docker and orchestrate with Kubernetes. "
            "Each component scales independently based on its specific resource "
            "requirements. Use HorizontalPodAutoscaler for API services and "
            "StatefulSets for the vector database.\n\n"
            "## Monitoring and Observability\n\n"
            "Track P50, P95, and P99 latency for each pipeline stage. Monitor hit rate, "
            "MRR, cache hit ratio, and error rates. Use Prometheus for metrics "
            "collection and Grafana for visualization. Set up alerts for critical "
            "threshold violations.\n\n"
            "## Conclusion\n\n"
            "Building a production RAG pipeline requires careful attention to each "
            "component. Start with a simple implementation, measure everything, and "
            "optimize based on real metrics. The techniques covered in this guide "
            "will help you achieve a system that is both accurate and performant "
            "at scale.\n\n"
            "### Further Reading\n\n"
            "- LangChain documentation on RAG pipelines\n"
            "- ChromaDB production deployment guide\n"
            "- OpenAI embeddings documentation\n"
            "- Kubernetes best practices for AI workloads\n\n"
            "---\n\n"
            "*Found this guide helpful? Subscribe to the channel for more AI "
            "engineering tutorials. The complete code is available on GitHub.*"
        ),
        "sections": [
            {
                "heading": "What is Retrieval-Augmented Generation?",
                "content": "RAG is an AI architecture that combines document retrieval with generative language models...",
                "word_count": 180,
                "has_code": False,
            },
            {
                "heading": "Architecture Overview",
                "content": "A production RAG pipeline consists of several components that work together...",
                "word_count": 220,
                "has_code": False,
            },
            {
                "heading": "Semantic Chunking Strategies",
                "content": "Chunking is the most critical preprocessing step. Poor chunking produces poor results...",
                "word_count": 250,
                "has_code": True,
            },
            {
                "heading": "Query Rewriting",
                "content": "Query rewriting uses an LLM to transform user questions into more effective search queries...",
                "word_count": 195,
                "has_code": True,
            },
            {
                "heading": "Production Deployment",
                "content": "Containerize each component with Docker and orchestrate with Kubernetes...",
                "word_count": 210,
                "has_code": True,
            },
        ],
        "metadata": {
            "author": "AI Blog Generator",
            "created": "2025-12-10T14:30:00Z",
            "updated": "2025-12-10T16:45:00Z",
            "version": "1.3",
            "status": "completed",
            "word_count": 2450,
            "read_time": "12 min",
            "primary_keyword": "RAG pipeline tutorial",
            "has_callout_boxes": False,
            "has_tables": False,
            "has_code_blocks": True,
            "has_faq_section": False,
            "estimated_seo_score": 82.0,
        },
        "word_count": 2450,
        "read_time": "12 min",
        "toc": [
            {"title": "Introduction", "level": 2, "anchor": "introduction"},
            {"title": "What is Retrieval-Augmented Generation?", "level": 2, "anchor": "what-is-rag"},
            {"title": "Why RAG Matters for Enterprise AI", "level": 3, "anchor": "why-rag-matters"},
            {"title": "How RAG Differs from Fine-Tuning", "level": 3, "anchor": "rag-vs-fine-tuning"},
            {"title": "Architecture Overview", "level": 2, "anchor": "architecture"},
            {"title": "Semantic Chunking Strategies", "level": 2, "anchor": "chunking"},
            {"title": "Query Rewriting", "level": 2, "anchor": "query-rewriting"},
            {"title": "Production Deployment", "level": 2, "anchor": "deployment"},
            {"title": "Monitoring", "level": 2, "anchor": "monitoring"},
            {"title": "Conclusion", "level": 2, "anchor": "conclusion"},
        ],
        "references": [
            {"title": "LangChain RAG Documentation", "url": "https://python.langchain.com/docs/use_cases/question_answering/"},
            {"title": "ChromaDB Getting Started", "url": "https://docs.trychroma.com/getting-started"},
            {"title": "OpenAI Embeddings Guide", "url": "https://platform.openai.com/docs/guides/embeddings"},
        ],
    }


def sample_draft_versions() -> list[dict[str, Any]]:
    return [
        {
            "version": 1,
            "title": "Building a RAG Pipeline",
            "status": "draft",
            "word_count": 1800,
            "created": "2025-12-09T10:00:00Z",
            "changes": "Initial draft with core architecture and chunking sections",
            "content_preview": "# Building a RAG Pipeline\n\n## Introduction\n\nRAG is an AI architecture...",
        },
        {
            "version": 2,
            "title": "Building a RAG Pipeline: Complete Guide",
            "status": "review",
            "word_count": 2200,
            "created": "2025-12-10T09:30:00Z",
            "changes": "Added query rewriting, reranking, and deployment sections",
            "content_preview": "# Building a RAG Pipeline: Complete Guide\n\n## Introduction\n\nRAG is an AI architecture...",
        },
        {
            "version": 3,
            "title": "Building a Production-Grade RAG Pipeline: Complete Guide 2025",
            "status": "completed",
            "word_count": 2450,
            "created": "2025-12-10T16:45:00Z",
            "changes": "SEO optimization, added benchmark results, final polish",
            "content_preview": "# Building a Production-Grade RAG Pipeline: Complete Guide 2025\n\n## Introduction\n\nYour RAG pipeline is too slow...",
        },
    ]


def sample_draft_metadata() -> dict[str, Any]:
    return {
        "author": "AI Blog Generator",
        "created": "2025-12-10T14:30:00Z",
        "updated": "2025-12-10T16:45:00Z",
        "version": 3,
        "status": "completed",
        "total_edits": 3,
        "time_to_complete_hours": 6.25,
        "llm_provider": "gpt-4o-mini",
        "total_tokens_used": 15200,
        "estimated_cost_usd": 0.045,
    }
