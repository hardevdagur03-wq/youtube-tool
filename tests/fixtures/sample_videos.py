from __future__ import annotations

from typing import Any


def sample_video_metadata() -> dict[str, Any]:
    return {
        "video_id": "dQw4w9WgXcQ",
        "title": "Building a Production-Ready RAG Pipeline from Scratch",
        "description": (
            "In this comprehensive tutorial, we build a production-grade "
            "Retrieval-Augmented Generation pipeline using LangChain, "
            "ChromaDB, and OpenAI embeddings. We cover chunking strategies, "
            "vector indexing, query optimization, and deployment best "
            "practices for handling millions of documents at scale."
        ),
        "channel_id": "UCtechChannel12345",
        "channel_title": "TechWithAlex",
        "published_at": "2025-11-15T14:30:00Z",
        "duration_seconds": 2847,
        "view_count": 845912,
        "like_count": 42351,
        "comment_count": 1892,
        "tags": [
            "rag", "langchain", "chromadb", "vector database",
            "retrieval augmented generation", "llm", "openai",
            "embeddings", "machine learning", "ai engineering",
        ],
        "category_id": "28",
        "thumbnails": {
            "default": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg", "width": 120, "height": 90},
            "medium": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg", "width": 320, "height": 180},
            "high": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg", "width": 480, "height": 360},
            "maxres": {"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg", "width": 1280, "height": 720},
        },
    }


def sample_video_urls() -> list[str]:
    return [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/jNQXAC9IVRw",
        "https://www.youtube.com/watch?v=9bZkp7q19f0&t=30s",
        "https://youtube.com/shorts/zB4I68XQz0k",
        "https://www.youtube.com/watch?v=kJQP7kiw5Fk&list=PLabc123",
        "https://youtu.be/_VB39Jo8mAQ?si=test1234",
    ]


def sample_channel_data() -> dict[str, Any]:
    return {
        "channel_id": "UCtechChannel12345",
        "title": "TechWithAlex",
        "description": "Deep dives into software engineering, AI, and system design.",
        "custom_url": "@TechWithAlex",
        "published_at": "2020-03-12T10:00:00Z",
        "country": "US",
        "subscriber_count": 892000,
        "video_count": 423,
        "view_count": 45600000,
        "topic_categories": [
            "https://en.wikipedia.org/wiki/Software_engineering",
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
        ],
        "keywords": ["programming", "ai", "machine learning", "system design"],
        "is_verified": True,
    }


def sample_video_list() -> list[dict[str, Any]]:
    return [
        {
            "video_id": "abc123def45",
            "title": "Kubernetes in Production: Lessons Learned from 3 Years of Operations",
            "description": "Real-world experiences running Kubernetes clusters in production.",
            "channel_id": "UCdevopsChannel",
            "channel_title": "DevOpsPro",
            "published_at": "2025-10-01T09:00:00Z",
            "duration_seconds": 3600,
            "view_count": 234000,
            "like_count": 15200,
            "comment_count": 845,
            "tags": ["kubernetes", "devops", "production", "sre", "containers"],
            "category_id": "28",
        },
        {
            "video_id": "ghi789jkl01",
            "title": "Designing Data-Intensive Applications: A Visual Summary",
            "description": "Visual walkthrough of key concepts from the DDIA book.",
            "channel_id": "UCsysdesignChannel",
            "channel_title": "SystemDesignHQ",
            "published_at": "2025-09-22T16:00:00Z",
            "duration_seconds": 2400,
            "view_count": 567800,
            "like_count": 38900,
            "comment_count": 2100,
            "tags": ["system design", "distributed systems", "ddia", "architecture"],
            "category_id": "27",
        },
        {
            "video_id": "mno234pqr56",
            "title": "Fine-Tuning LLMs with LoRA: A Step-by-Step Guide",
            "description": "Complete guide to parameter-efficient fine-tuning using LoRA and QLoRA.",
            "channel_id": "UCmlChannel",
            "channel_title": "MLMastery",
            "published_at": "2025-12-05T11:30:00Z",
            "duration_seconds": 4200,
            "view_count": 1234000,
            "like_count": 78200,
            "comment_count": 3400,
            "tags": ["lora", "qlora", "fine-tuning", "llm", "transformers", "huggingface"],
            "category_id": "28",
        },
    ]
