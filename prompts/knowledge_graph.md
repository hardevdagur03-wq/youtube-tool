---
prompt_id: p_kg_v1
name: Knowledge Graph Builder
version: 1.0.0
author: Platform Team
status: production
category: knowledge_graph
tags: [knowledge-graph, entities, relationships]
language: en
target_model: gemini-2.0-flash
temperature: 0.2
max_tokens: 8192
created: 2026-07-01
updated: 2026-07-01
owner: AI Pipeline Team
approval: approved
risk_level: medium
supported_models: [gemini-2.0-flash, gemini-2.5-pro, gpt-4o, claude-3-sonnet]
dependencies: [analysis]
change_log:
  - version: 1.0.0
    date: 2026-07-01
    author: Platform Team
    summary: Initial production prompt
    changes: created
---

You are a knowledge graph construction specialist.

Build a comprehensive knowledge graph from the following video transcript and analysis.

TRANSCRIPT:
{{transcript}}

ANALYSIS:
{{analysis}}

VIDEO METADATA:
Title: {{title}}
Channel: {{channel}}
Category: {{category}}
Tags: {{tags}}

Extract entities and their relationships to build a structured knowledge graph.

Return the knowledge graph in this JSON structure:
{
  "entities": [
    {
      "id": "unique-entity-id",
      "name": "Entity Name",
      "type": "concept|person|organization|product|technology|location|event|field|tool|framework",
      "description": "Brief description",
      "aliases": ["alias1", "alias2"],
      "relevance_score": 0.0-1.0,
      "mentions": [
        {"context": "surrounding text", "timestamp": "00:00:00", "sentiment": "positive|negative|neutral"}
      ],
      "properties": {"key": "value"}
    }
  ],
  "relationships": [
    {
      "source_id": "entity-id-1",
      "target_id": "entity-id-2",
      "relationship_type": "part_of|used_by|related_to|precedes|follows|contradicts|supports|example_of|causes|requires",
      "description": "Nature of relationship",
      "weight": 0.0-1.0,
      "evidence": ["supporting quote from transcript"]
    }
  ],
  "categories": [
    {
      "name": "Category Name",
      "entities": ["entity-id-1"],
      "subcategories": []
    }
  ],
  "summary": {
    "total_entities": 0,
    "total_relationships": 0,
    "density": 0.0-1.0,
    "central_topics": ["topic1"],
    "knowledge_gaps": ["missing information"]
  }
}

Be precise. Only include entities and relationships explicitly supported by the transcript.
