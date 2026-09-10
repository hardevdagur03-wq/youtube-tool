"""Versioned prompt templates for AI content analysis."""

from __future__ import annotations

PROMPT_VERSION = "1.0.0"

SYSTEM_PROMPT = """You are an expert AI content analyst specializing in video transcript analysis.
Your role is to extract structured semantic knowledge from transcripts.
You do NOT generate blog posts or marketing copy.
You do NOT rewrite the content.
You produce structured JSON data only.

Rules:
1. Be factual — only extract information present in the transcript.
2. Do NOT hallucinate keywords, entities, or topics not mentioned.
3. When uncertain, use empty lists rather than guesses.
4. Keep summaries concise and factual.
5. Quality scores must be data-driven based on transcript characteristics.

Output ONLY valid JSON matching the requested schema."""

ANALYSIS_PROMPT = """Analyze the following video transcript and extract structured semantic knowledge.

TRANSCRIPT:
{transcript}

CONTEXT:
- Video ID: {video_id}
- Category hints: {categories}
- Language: {language}

Extract and return a JSON object with this exact structure:
{{
  "primary_topic": "The single most relevant topic (6 words max)",
  "secondary_topics": ["topic2", "topic3", "topic4", "topic5"],
  "category": "One of: education, technology, finance, healthcare, politics, career, programming, ai, machine_learning, business, marketing, lifestyle, science, entertainment, sports, news",
  "subcategory": "More specific subcategory (2-3 words)",
  "content_type": "One of: tutorial, explainer, review, opinion, case_study, interview, presentation, discussion, documentary, vlog, podcast",
  "search_intent": "One of: informational, educational, commercial, transactional, navigational, comparative, review, tutorial, opinion, case_study, research",
  "intent_confidence": 0.0-1.0,
  "target_audience": "Who this is for (e.g. 'Software developers', 'Students', 'General audience')",
  "experience_level": "beginner|intermediate|advanced|expert|all",
  "industry": "Primary industry",
  "difficulty": "beginner|intermediate|advanced|expert",
  "content_purpose": "Why this content exists",
  "problem_statement": "What problem does this address?",
  "main_solution": "What solution is presented?",
  "key_takeaways": ["takeaway1", "takeaway2"],
  "pain_points": ["pain1", "pain2"],
  "opportunities": ["opportunity1"],
  "action_items": ["action1", "action2"],
  "call_to_actions": ["cta1"],
  "learning_objectives": ["objective1"],
  "business_value": "Business relevance",
  "educational_value": "Educational relevance",
  "summary": {{
    "short": "One sentence summary (20 words max)",
    "executive": "Executive summary (3 sentences max)",
    "detailed": "Detailed summary (paragraph)",
    "bullet_points": ["point1", "point2", "point3"],
    "key_insights": ["insight1"],
    "main_arguments": ["argument1"],
    "important_facts": ["fact1"],
    "actionable_points": ["actionable1"]
  }},
  "keywords": {{
    "primary": "Primary keyword",
    "secondary": ["keyword1", "keyword2", "keyword3"],
    "long_tail": ["long tail keyword phrase"],
    "semantic": ["semantically related term"],
    "lsi": ["LSI keyword"],
    "related_topics": ["related topic"],
    "trending_terms": [],
    "brand_names": [],
    "products": ["mentioned product"],
    "technologies": ["mentioned technology"],
    "frameworks": ["mentioned framework"]
  }},
  "entities": {{
    "people": [],
    "companies": [],
    "organizations": [],
    "universities": [],
    "countries": [],
    "cities": [],
    "technologies": [],
    "programming_languages": [],
    "frameworks": [],
    "books": [],
    "courses": [],
    "tools": [],
    "products": [],
    "standards": [],
    "government_agencies": [],
    "dates": [],
    "statistics": []
  }},
  "outline": {{
    "sections": ["Section 1", "Section 2", "Section 3", "Section 4", "Section 5"],
    "introduction": "What does the introduction cover?",
    "main_body": ["Body section 1", "Body section 2"],
    "conclusion": "What does the conclusion cover?"
  }},
  "quality": {{
    "topic_coverage": 0-100,
    "depth_score": 0-100,
    "readability": 0-100,
    "information_density": 0-100,
    "technical_complexity": 0-100,
    "educational_value": 0-100,
    "uniqueness": 0-100,
    "seo_potential": 0-100,
    "evergreen_score": 0-100,
    "engagement_potential": 0-100,
    "confidence": 0.0-1.0
  }}
}}

Return ONLY the JSON object. No markdown, no explanation."""
