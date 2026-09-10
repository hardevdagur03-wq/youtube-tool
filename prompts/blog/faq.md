PROMPT_VERSION = "1.0.0"
Generate FAQ items for a blog post from this context.

TOPIC: {primary_topic}
AUDIENCE: {target_audience}

KEY INSIGHTS:
{key_insights}

FACTS:
{important_facts}

TRANSCRIPT:
{transcript}

Generate 5-10 FAQ items as a JSON array:
[
  {{"question": "Question?", "answer": "Answer from transcript only."}}
]
