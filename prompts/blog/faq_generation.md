PROMPT_VERSION = "1.0.0"
Generate an FAQ section for a blog post based on the following structured context.

TRANSCRIPT CONTEXT:
{transcript}

PRIMARY TOPIC: {primary_topic}
SECONDARY TOPICS: {secondary_topics}
TARGET AUDIENCE: {target_audience}

KEY INSIGHTS:
{key_insights}

IMPORTANT FACTS:
{important_facts}

Generate 3-6 FAQ items as a JSON array. Each item must be a question that the transcript actually answers and a concise answer drawn only from transcript content.

Format:
[
  {{
    "question": "Question text?",
    "answer": "Answer text based only on transcript facts."
  }}
]

Return ONLY the JSON array. No markdown, no explanation.
