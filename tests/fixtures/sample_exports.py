from __future__ import annotations

from typing import Any


def sample_export_result() -> dict[str, Any]:
    return {
        "format": "markdown",
        "content": sample_markdown_export(),
        "metadata": {
            "title": "Building a Production-Grade RAG Pipeline: Complete Guide 2025",
            "author": "AI Blog Generator",
            "date": "2025-12-10",
            "word_count": 2450,
            "format": "markdown",
            "version": "1.3",
            "primary_keyword": "RAG pipeline tutorial",
            "estimated_seo_score": 86.5,
        },
        "success": True,
        "file_path": "/exports/rag-pipeline-guide-2025.md",
        "file_size": 18450,
        "duration_ms": 1250,
    }


def sample_markdown_export() -> str:
    return (
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
        "## Architecture Overview\n\n"
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
        "## Query Rewriting\n\n"
        "Query rewriting uses an LLM to transform user questions into more effective "
        "search queries. This resolves ambiguity, incorporates conversation history, "
        "and matches document vocabulary. Our benchmarks show a 15 percent "
        "improvement in hit rate with this technique.\n\n"
        "## Cross-Encoder Reranking\n\n"
        "After initial retrieval, a cross-encoder model reranks the results by "
        "evaluating the relevance of each chunk against the query. This adds 50 "
        "milliseconds of latency but significantly improves the quality of top "
        "results.\n\n"
        "## Production Deployment\n\n"
        "Containerize each component with Docker and orchestrate with Kubernetes. "
        "Each component scales independently based on its specific resource "
        "requirements. Use HorizontalPodAutoscaler for API services and "
        "StatefulSets for the vector database.\n\n"
        "## Monitoring and Observability\n\n"
        "Track P50, P95, and P99 latency for each pipeline stage using Prometheus "
        "and Grafana. Monitor hit rate, MRR, cache hit ratio, and error rates. "
        "Set up alerts for critical threshold violations.\n\n"
        "## Conclusion\n\n"
        "Building a production RAG pipeline requires careful attention to each "
        "component. Start with a simple implementation, measure everything, and "
        "optimize based on real metrics. The techniques covered in this guide "
        "will help you achieve a system that is both accurate and performant.\n\n"
        "### Further Reading\n\n"
        "- [LangChain RAG Documentation](https://python.langchain.com/docs/use_cases/question_answering/)\n"
        "- [ChromaDB Production Guide](https://docs.trychroma.com/production)\n"
        "- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)\n\n"
        "---\n\n"
        "*Found this guide helpful? Subscribe for more AI engineering tutorials. "
        "Full code available on GitHub.*\n"
    )


def sample_html_export() -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        "<title>Building a Production-Grade RAG Pipeline: Complete Guide 2025</title>\n"
        '<meta name="description" content="Learn to build a production RAG pipeline with LangChain and ChromaDB. Covers semantic chunking, query rewriting, and Kubernetes deployment.">\n'
        '<meta name="keywords" content="RAG pipeline, LangChain, ChromaDB, vector database, retrieval augmented generation">\n'
        "</head>\n"
        "<body>\n"
        '<article itemscope itemtype="https://schema.org/TechArticle">\n'
        '<h1 itemprop="name">Building a Production-Grade RAG Pipeline: Complete Guide 2025</h1>\n'
        '<meta itemprop="author" content="AI Blog Generator">\n'
        '<meta itemprop="datePublished" content="2025-12-10">\n'
        '<meta itemprop="wordCount" content="2450">\n'
        '<section itemprop="articleBody">\n'
        "<h2>Introduction</h2>\n"
        "<p>Your RAG pipeline is too slow. The chunks are wrong. The answers are "
        "hallucinated. If you have tried to deploy a production RAG system, you "
        "have likely faced these challenges. This guide will walk you through "
        "building a RAG pipeline that achieves 94 percent hit rate with "
        "sub-second latency.</p>\n"
        "<h2>What is Retrieval-Augmented Generation?</h2>\n"
        "<p>RAG is an AI architecture that combines document retrieval with generative "
        "language models. Instead of relying solely on the model's internal knowledge, "
        "RAG first retrieves relevant documents from a knowledge base and uses them "
        "as context for generation. This dramatically reduces hallucinations.</p>\n"
        "<h2>Semantic Chunking Strategies</h2>\n"
        "<p>Chunking is the most critical preprocessing step. Poor chunking produces "
        "poor results regardless of other optimizations. Semantic chunking respects "
        "natural language boundaries rather than cutting at arbitrary token counts.</p>\n"
        "<h3>Recursive Character Text Splitting</h3>\n"
        "<p>The RecursiveCharacterTextSplitter from LangChain uses a hierarchy of "
        "separators to split documents. It first tries double newlines, then single "
        "newlines, then periods, and finally characters.</p>\n"
        "<h3>Chunk Overlap Configuration</h3>\n"
        "<p>A standard configuration uses 512 token chunks with 64 tokens of overlap. "
        "This prevents context loss at chunk boundaries.</p>\n"
        "<h2>Conclusion</h2>\n"
        "<p>Building a production RAG pipeline requires careful attention to each "
        "component. Start simple, measure everything, and optimize based on real metrics.</p>\n"
        "</section>\n"
        "</article>\n"
        "</body>\n"
        "</html>\n"
    )


def sample_export_metadata() -> dict[str, Any]:
    return {
        "title": "Building a Production-Grade RAG Pipeline: Complete Guide 2025",
        "author": "AI Blog Generator",
        "date": "2025-12-10",
        "word_count": 2450,
        "format": "markdown",
        "version": "1.3",
        "primary_keyword": "RAG pipeline tutorial",
        "estimated_seo_score": 86.5,
        "reading_time_minutes": 12,
        "includes_code": True,
        "includes_tables": False,
        "includes_images": False,
        "section_count": 8,
        "export_timestamp": "2025-12-10T17:00:00Z",
        "generator_version": "7.0.0",
    }
