---
template_id: t_blog_post_v1
name: Standard Blog Post Template
version: 1.0.0
type: template
components: [system_prompt, writing_style, seo_rules, output_format, brand_voice, citation_rules]
---

# System Prompt
{{>system_prompt}}

# Writing Style
{{>writing_style}}

# SEO Rules
{{>seo_rules}}

# Output Format
{{>output_format}}

# Brand Voice
{{>brand_voice}}

# Citation Rules
{{>citation_rules}}

---

## Context

**Topic:** {{title}}
**Target Audience:** {{audience}}
**Tone:** {{tone}}
**Primary Keyword:** {{focus_keyword}}
**Word Count Target:** {{word_count}}

**Knowledge Graph Context:**
{{knowledge_graph}}

**SEO Strategy:**
{{seo_strategy}}

**Content Outline:**
{{outline}}

---

## Content Sections

{{sections}}

---

## Summary Requirements

{{>summary_requirements}}
