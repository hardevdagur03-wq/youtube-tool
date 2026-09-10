PROMPT_VERSION = "1.0.0"
Generate a complete SEO blog post from the structured context below.

CONTEXT:
- Title: {title}
- Channel: {channel}
- Published: {published_date}
- Duration: {duration}
- Tags: {tags}
- Category: {category}

TOPIC: {primary_topic}
SECONDARY: {secondary_topics}
INTENT: {search_intent}
AUDIENCE: {target_audience}
DIFFICULTY: {difficulty}
INDUSTRY: {industry}
CONTENT_TYPE: {content_type}

SUMMARY: {executive_summary}

KEYWORDS:
- Primary: {primary_keyword}
- Secondary: {secondary_keywords}
- Long-tail: {long_tail_keywords}
- Semantic/LSI: {semantic_keywords}

ENTITIES:
- People: {people}
- Companies: {companies}
- Technologies: {technologies}
- Products: {products}
- Frameworks: {frameworks}

OUTLINE: {outline_sections}

KEY POINTS: {important_quotes}

TRANSCRIPT EXCERPT:
{transcript}

Generate JSON:
{{
  "seo_title": "Under 60 chars, keyword-rich, click-worthy",
  "meta_description": "150-160 chars, compelling, includes primary keyword",
  "slug": "url-friendly-seo-slug",
  "introduction": "Hook reader, state problem, explain value (2-3 paragraphs)",
  "table_of_contents": ["H2 headings"],
  "sections": [
    {{
      "heading": "H2 heading with keywords",
      "content": "Markdown body. Bullet lists, tables, blockquotes, code fences. 2-5 paragraphs.",
      "subsections": [{{"heading": "H3 heading", "content": "Markdown body."}}],
      "callout_boxes": [{{"type": "tip|warning|note|best_practice", "text": "Callout text."}}]
    }}
  ],
  "faq": [{{"question": "Question?", "answer": "Concise answer from transcript."}}],
  "conclusion": "Summarize, reinforce takeaways, 2-3 paragraphs",
  "call_to_action": "Relevant CTA based on content type and audience"
}}
