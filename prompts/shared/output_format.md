---
partial_id: partial_output_format_v1
name: Output Format Rules
version: 1.0.0
type: partial
---

## Output Format Requirements

1. Return valid JSON only when JSON format is specified
2. All markdown must be well-formed with proper nesting
3. Code blocks use triple backticks with language specification
4. Links use standard markdown format: [text](url)
5. Images include alt text: ![alt](url)
6. Tables use pipe-separated markdown format
7. Lists are consistently formatted (all `-` or all `*`)
8. Headings have a space after `#` characters
9. No trailing whitespace on lines
10. Files end with a single newline
11. Bold uses `**text**` not `__text__`
12. Italic uses `*text*` not `_text_`
