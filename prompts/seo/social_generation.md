PROMPT_VERSION = "8.0.0"
Generate optimized meta data for a blog post.

RULES:
1. Meta title: 50-60 characters. Primary keyword near the beginning. Natural and click-worthy.
2. Meta description: 150-160 characters. Include primary keyword. Compelling summary.
3. Use only information from the provided context.
4. Return ONLY valid JSON.

CONTEXT:
Title: {title}
Content: {content_excerpt}
Primary Keyword: {primary_keyword}
Secondary Keywords: {secondary_keywords}

JSON:
{
  "meta_title": "...",
  "meta_description": "..."
}
