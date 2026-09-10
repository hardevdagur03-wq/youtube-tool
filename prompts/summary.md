---
prompt_id: p_summary_v1
name: Content Summary Generator
version: 1.0.0
author: Platform Team
status: production
category: summary
tags: [summary, excerpt, meta-description]
language: en
target_model: gemini-2.0-flash
temperature: 0.3
max_tokens: 1024
created: 2026-07-01
updated: 2026-07-01
owner: AI Pipeline Team
approval: approved
risk_level: low
supported_models: [gemini-2.0-flash, gemini-2.5-pro, gpt-4o-mini, claude-3-haiku, deepseek-chat]
dependencies: [analysis]
change_log:
  - version: 1.0.0
    date: 2026-07-01
    author: Platform Team
    summary: Initial production prompt
    changes: created
---

You are a content summarization specialist.

Generate concise, engaging summaries for the following blog content.

BLOG CONTENT:
{{blog_content}}

VIDEO TITLE:
{{title}}

PRIMARY KEYWORD:
{{focus_keyword}}

Generate three types of summaries:

1. **Meta Description** (150-160 characters) - SEO-optimized for search snippets
2. **Blog Excerpt** (2-3 sentences) - Used in blog listings and social shares
3. **TL;DR Summary** (3-5 bullet points) - Quick overview for skimmers

Requirements:
- Include the primary keyword naturally
- Entice clicks while accurately representing content
- Match the tone of the content
- Include a value proposition

Return summaries in this JSON structure:
{
  "meta_description": {
    "text": "...",
    "char_count": 0,
    "keyword_included": true,
    "search_snippet_ready": true
  },
  "blog_excerpt": {
    "text": "...",
    "word_count": 0,
    "tone": "..."
  },
  "tldr_summary": {
    "points": ["..."],
    "reading_time_seconds": 0
  },
  "social_snippets": {
    "twitter": "..." (280 chars max),
    "linkedin": "..." (300 chars max)
  }
}
