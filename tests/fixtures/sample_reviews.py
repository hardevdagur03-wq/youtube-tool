from __future__ import annotations

from typing import Any


def sample_review() -> dict[str, Any]:
    return {
        "overall_score": 86.5,
        "section_scores": {
            "introduction": 88.0,
            "body_what_is_rag": 85.0,
            "body_architecture": 82.0,
            "body_chunking": 90.0,
            "body_query_rewriting": 87.0,
            "body_reranking": 84.0,
            "body_deployment": 86.0,
            "body_monitoring": 85.0,
            "conclusion": 89.0,
        },
        "validators_results": [
            {"validator": "grammar", "score": 94.5, "passed": True, "issues": 3},
            {"validator": "readability", "score": 78.0, "passed": True, "issues": 2},
            {"validator": "seo", "score": 88.0, "passed": True, "issues": 1},
            {"validator": "content_quality", "score": 85.0, "passed": True, "issues": 2},
            {"validator": "completeness", "score": 82.0, "passed": True, "issues": 2},
            {"validator": "fact_consistency", "score": 92.0, "passed": True, "issues": 0},
            {"validator": "heading_quality", "score": 90.0, "passed": True, "issues": 0},
            {"validator": "duplicate_content", "score": 96.0, "passed": True, "issues": 0},
            {"validator": "markdown_quality", "score": 88.0, "passed": True, "issues": 1},
            {"validator": "ai_detection", "score": 72.0, "passed": False, "issues": 3},
            {"validator": "e_e_a_t", "score": 80.0, "passed": True, "issues": 2},
            {"validator": "accessibility", "score": 75.0, "passed": True, "issues": 4},
            {"validator": "passive_voice", "score": 85.0, "passed": True, "issues": 5},
        ],
        "recommendations": [
            {
                "category": "readability",
                "priority": "high",
                "description": "Reduce average sentence length from 22 to under 18 words",
                "impact": 0.12,
            },
            {
                "category": "seo",
                "priority": "medium",
                "description": "Add primary keyword to the conclusion section",
                "impact": 0.08,
            },
            {
                "category": "ai_detection",
                "priority": "high",
                "description": "Add more personal anecdotes and unique examples to reduce AI detection score",
                "impact": 0.15,
            },
            {
                "category": "accessibility",
                "priority": "medium",
                "description": "Add alt text descriptions to all code block screenshots",
                "impact": 0.05,
            },
            {
                "category": "content",
                "priority": "medium",
                "description": "Add a comparison table for vector database options",
                "impact": 0.10,
            },
            {
                "category": "passive_voice",
                "priority": "low",
                "description": "Rewrite passive voice constructions in 5 sentences",
                "impact": 0.03,
            },
        ],
        "issues": [
            {
                "severity": "medium",
                "type": "readability",
                "description": "Several sentences exceed 30 words, reducing readability",
                "suggestion": "Break long sentences into shorter ones. Target maximum 20 words per sentence.",
                "location": "Architecture Overview section",
            },
            {
                "severity": "medium",
                "type": "ai_detection",
                "description": "Content structure is highly consistent which may indicate AI generation",
                "suggestion": "Vary paragraph lengths and add more varied transitions between sections.",
                "location": "Throughout",
            },
            {
                "severity": "low",
                "type": "passive_voice",
                "description": "Each section contains approximately 2-3 passive voice constructions",
                "suggestion": "Replace passive voice with active constructions where possible.",
                "location": "Body sections",
            },
            {
                "severity": "low",
                "type": "accessibility",
                "description": "Code blocks are not accompanied by explanatory text for screen readers",
                "suggestion": "Add descriptive text before code blocks explaining what they demonstrate.",
                "location": "Chunking and Deployment sections",
            },
            {
                "severity": "low",
                "type": "seo",
                "description": "Meta description could be more compelling to improve click-through rate",
                "suggestion": "Include a specific number or statistic in the meta description.",
                "location": "Meta tags",
            },
            {
                "severity": "info",
                "type": "completeness",
                "description": "FAQ section is missing from the blog post",
                "suggestion": "Add an FAQ section addressing common questions about RAG pipelines.",
                "location": "After conclusion",
            },
        ],
        "strengths": [
            "Comprehensive coverage of all major RAG pipeline components",
            "Excellent fact consistency with no contradictions found",
            "Well-structured heading hierarchy with logical progression",
            "Good keyword usage throughout without stuffing",
            "Strong technical depth appropriate for the target audience",
            "Code examples are accurate and well-explained",
        ],
        "summary": (
            "The draft is production-ready with an overall score of 86.5 out of 100. "
            "Content quality and technical accuracy are strong. The main areas for "
            "improvement are reducing AI detection signals by adding more unique "
            "examples, improving accessibility for code blocks, and adding an FAQ "
            "section. Minor readability and SEO tweaks will bring the score above 90."
        ),
    }


def sample_review_scores() -> dict[str, float]:
    return {
        "grammar": 94.5,
        "readability": 78.0,
        "seo": 88.0,
        "content_quality": 85.0,
        "completeness": 82.0,
        "fact_consistency": 92.0,
        "heading_quality": 90.0,
        "duplicate_content": 96.0,
        "markdown_quality": 88.0,
        "ai_detection": 72.0,
        "e_e_a_t": 80.0,
        "accessibility": 75.0,
        "passive_voice": 85.0,
    }


def sample_review_issues() -> list[dict[str, Any]]:
    return [
        {
            "severity": "high",
            "type": "readability",
            "description": "Average sentence length of 22 words exceeds recommended maximum of 18",
            "suggestion": "Break compound sentences into simpler structures for better readability.",
        },
        {
            "severity": "high",
            "type": "ai_detection",
            "description": "AI detection probability is 72 percent, exceeding the 50 percent threshold",
            "suggestion": "Add personal experiences, unique metaphors, and vary sentence structure.",
        },
        {
            "severity": "medium",
            "type": "completeness",
            "description": "FAQ section is missing which reduces comprehensiveness",
            "suggestion": "Add 3-5 frequently asked questions about RAG pipeline implementation.",
        },
        {
            "severity": "medium",
            "type": "seo",
            "description": "Primary keyword does not appear in the conclusion section",
            "suggestion": "Mention the primary keyword naturally in the concluding paragraph.",
        },
        {
            "severity": "low",
            "type": "passive_voice",
            "description": "Five sentences use passive voice which reduces engagement",
            "suggestion": "Rewrite to active voice: 'The chunking strategy is configured' becomes 'Configure the chunking strategy'.",
        },
        {
            "severity": "low",
            "type": "accessibility",
            "description": "Code blocks lack screen-reader-friendly descriptions",
            "suggestion": "Precede each code block with a descriptive sentence explaining its purpose.",
        },
        {
            "severity": "info",
            "type": "structure",
            "description": "No visual elements like tables or diagrams present",
            "suggestion": "Consider adding a comparison table for vector database options.",
        },
    ]
