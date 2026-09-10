from __future__ import annotations

from typing import Any


def sample_transcript_segments() -> list[dict[str, Any]]:
    return [
        {"text": "Welcome back to the channel everyone.", "start": 0.0, "duration": 2.5},
        {"text": "Today we're going to build a production-grade RAG pipeline", "start": 2.5, "duration": 3.2},
        {"text": "using LangChain, ChromaDB, and OpenAI embeddings.", "start": 5.7, "duration": 3.0},
        {"text": "If you've been following along with this series,", "start": 8.7, "duration": 2.8},
        {"text": "you already know the basics of working with LLMs.", "start": 11.5, "duration": 2.5},
        {"text": "Now it's time to scale things up for production.", "start": 14.0, "duration": 2.2},
        {"text": "Let me start by explaining what RAG actually means.", "start": 16.2, "duration": 3.0},
        {"text": "RAG stands for Retrieval-Augmented Generation.", "start": 19.2, "duration": 2.5},
        {"text": "It's a technique that combines a retrieval system", "start": 21.7, "duration": 2.8},
        {"text": "with a generative language model.", "start": 24.5, "duration": 2.0},
        {"text": "The key advantage is that it grounds the model's responses", "start": 26.5, "duration": 3.0},
        {"text": "in actual retrieved documents rather than relying solely", "start": 29.5, "duration": 2.5},
        {"text": "on the model's internal knowledge.", "start": 32.0, "duration": 2.0},
        {"text": "This dramatically reduces hallucinations.", "start": 34.0, "duration": 2.0},
        {"text": "For our architecture, we'll use a two-stage approach.", "start": 36.0, "duration": 2.5},
        {"text": "First, we index our documents into ChromaDB", "start": 38.5, "duration": 2.8},
        {"text": "using OpenAI's text-embedding-3-small model.", "start": 41.3, "duration": 2.5},
        {"text": "Then at query time, we embed the user's question,", "start": 43.8, "duration": 2.5},
        {"text": "retrieve the top-k most similar chunks,", "start": 46.3, "duration": 2.2},
        {"text": "and pass them as context to GPT-4o mini.", "start": 48.5, "duration": 2.5},
        {"text": "The chunking strategy is critical for RAG performance.", "start": 51.0, "duration": 3.0},
        {"text": "We're going to use semantic chunking with overlap.", "start": 54.0, "duration": 2.5},
        {"text": "Each chunk targets 512 tokens with 64 tokens of overlap.", "start": 56.5, "duration": 3.0},
        {"text": "This ensures we don't lose context at chunk boundaries.", "start": 59.5, "duration": 2.5},
        {"text": "For evaluation, we track hit rate and MRR.", "start": 62.0, "duration": 2.5},
        {"text": "Hit rate measures whether the relevant document is retrieved,", "start": 64.5, "duration": 3.0},
        {"text": "while MRR accounts for the ranking position.", "start": 67.5, "duration": 2.5},
    ]


def sample_full_transcript() -> str:
    return (
        "Welcome back to the channel everyone. Today we're going to build a production-grade "
        "RAG pipeline using LangChain, ChromaDB, and OpenAI embeddings. If you've been following "
        "along with this series, you already know the basics of working with LLMs. Now it's time "
        "to scale things up for production.\n\n"
        "Let me start by explaining what RAG actually means. RAG stands for Retrieval-Augmented "
        "Generation. It's a technique that combines a retrieval system with a generative language "
        "model. The key advantage is that it grounds the model's responses in actual retrieved "
        "documents rather than relying solely on the model's internal knowledge. This dramatically "
        "reduces hallucinations and improves factual accuracy.\n\n"
        "For our architecture, we'll use a two-stage approach. First, we index our documents into "
        "ChromaDB using OpenAI's text-embedding-3-small model. Then at query time, we embed the "
        "user's question, retrieve the top-k most similar chunks, and pass them as context to "
        "GPT-4o mini. The chunking strategy is critical for RAG performance.\n\n"
        "We're going to use semantic chunking with overlap. Each chunk targets 512 tokens with "
        "64 tokens of overlap. This ensures we don't lose context at chunk boundaries. For "
        "evaluation, we track hit rate and mean reciprocal rank. Hit rate measures whether the "
        "relevant document is retrieved, while MRR accounts for the ranking position.\n\n"
        "Let me walk through the code. First, we initialize our embedding model and vector store. "
        "We use OpenAIEmbeddings with the text-embedding-3-small model which gives us 1536 "
        "dimensional embeddings. For ChromaDB, we configure a persistent client with an "
        "in-memory fallback for testing. The collection uses cosine similarity as the distance "
        "metric.\n\n"
        "When loading documents, we use the RecursiveCharacterTextSplitter from LangChain. "
        "The chunk size is set to 512 tokens with a chunk overlap of 64 tokens. We also "
        "use the separators parameter to respect paragraph and sentence boundaries.\n\n"
        "For retrieval, we start with a simple top-k of 4 chunks. But in production you'll "
        "want to experiment with different values. We also implement a reranking step using "
        "a cross-encoder model to improve the quality of the retrieved results. This adds "
        "about 50 milliseconds of latency but significantly improves the relevance of the "
        "top results.\n\n"
        "The generation step uses GPT-4o mini with a system prompt that instructs the model "
        "to answer based solely on the provided context. We set the temperature to 0.2 for "
        "more deterministic outputs and limit the max tokens to 1024.\n\n"
        "One important optimization is query rewriting. Before retrieving, we have the LLM "
        "rewrite the user's question into a more effective search query. This handles cases "
        "where the user asks a vague question or refers to previous context.\n\n"
        "For production deployment, we containerize everything with Docker and use Kubernetes "
        "for orchestration. Each component scales independently: embedding, vector store, "
        "and generation. We use Redis for caching embeddings and responses, which gives us "
        "about 60 percent cache hit rate for common queries.\n\n"
        "Monitoring is done with Prometheus and Grafana. We track p50, p95, and p99 latency "
        "for each stage of the pipeline. The most important metric is end-to-end latency "
        "which should stay under 2 seconds for 95 percent of requests.\n\n"
        "Let me show you the benchmark results. On our test dataset of 1 million documents, "
        "the pipeline achieves a hit rate of 0.94 and MRR of 0.87. The average retrieval "
        "time is 45 milliseconds, and the full generation takes about 800 milliseconds. "
        "That's it for this tutorial. If you found it helpful, please like and subscribe. "
        "The full code is available on GitHub linked in the description."
    )


def sample_transcript_analysis() -> dict[str, Any]:
    return {
        "language": "en",
        "language_confidence": 0.99,
        "word_count": 487,
        "character_count": 3210,
        "duration_seconds": 2847,
        "estimated_read_time": "3 min",
        "unique_words": 312,
        "avg_word_length": 4.8,
        "avg_sentence_length": 18.5,
        "complexity_score": 0.65,
        "readability_score": 62.5,
        "sentiment": {
            "overall": "positive",
            "score": 0.72,
            "confidence": 0.89,
        },
        "speech_rate": 2.8,
        "pause_ratio": 0.15,
        "filled_pauses": 12,
        "topic_segments": [
            {"topic": "introduction", "start": 0.0, "end": 16.0},
            {"topic": "rag_explanation", "start": 16.0, "end": 36.0},
            {"topic": "architecture", "start": 36.0, "end": 51.0},
            {"topic": "implementation", "start": 51.0, "end": 80.0},
            {"topic": "deployment", "start": 80.0, "end": 100.0},
        ],
    }


def sample_processed_transcript() -> dict[str, Any]:
    return {
        "language": "en",
        "segments": sample_transcript_segments(),
        "word_count": 487,
        "plain_text": sample_full_transcript(),
        "has_timestamps": True,
        "source": "youtube",
        "provider": "auto_generated",
        "is_complete": True,
    }


def sample_transcript_in_different_languages() -> dict[str, dict[str, Any]]:
    return {
        "en": {
            "language": "en",
            "segments": [
                {"text": "Building a production RAG pipeline requires careful planning.", "start": 0.0, "duration": 3.0},
            ],
            "word_count": 10,
        },
        "es": {
            "language": "es",
            "segments": [
                {"text": "Construir un pipeline RAG de producción requiere una planificación cuidadosa.", "start": 0.0, "duration": 3.5},
            ],
            "word_count": 11,
        },
        "fr": {
            "language": "fr",
            "segments": [
                {"text": "Construire un pipeline RAG de production nécessite une planification minutieuse.", "start": 0.0, "duration": 3.5},
            ],
            "word_count": 12,
        },
        "de": {
            "language": "de",
            "segments": [
                {"text": "Der Aufbau einer Produktions-RAG-Pipeline erfordert sorgfältige Planung.", "start": 0.0, "duration": 3.2},
            ],
            "word_count": 10,
        },
    }


def sample_transcript_with_timestamps() -> dict[str, Any]:
    return {
        "segments": sample_transcript_segments(),
        "total_duration": 70.0,
        "has_timestamps": True,
        "segment_count": 27,
    }
