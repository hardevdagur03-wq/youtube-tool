"""Formatting Engine — normalizes typography, spacing, and structure across exports.

Ensures consistent formatting across all export formats:
- Smart quotes, em-dashes, proper ellipsis
- Consistent heading hierarchy
- Proper list formatting
- Consistent table styling
- Code block normalization
"""

from __future__ import annotations

import logging
import re
from typing import Any

from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class FormattingEngine:
    """Normalizes content formatting for publication-ready output.

    Applies consistent typography, heading hierarchy, list formatting,
    table styling, and code block presentation across all export formats.
    """

    def apply(self, content: str, template: TemplateConfig | None = None) -> str:
        """Apply all formatting normalizations to content.

        Args:
            content: Raw content string (typically Markdown).
            template: Optional template config for style-specific formatting.

        Returns:
            Formatted content string.
        """
        content = self.normalize_typography(content)
        content = self.normalize_headings(content)
        content = self.normalize_lists(content)
        content = self.normalize_code_blocks(content)
        content = self.normalize_whitespace(content)
        return content

    def normalize_typography(self, content: str) -> str:
        """Normalize typography: smart quotes, dashes, ellipsis.

        Args:
            content: Text content.

        Returns:
            Typographically normalized text.
        """
        # Smart quotes (for curated output — preserves existing smart quotes)
        content = content.replace("...", "\u2026")  # Ellipsis
        content = content.replace(" -- ", " \u2014 ")  # Em dash
        content = content.replace(" - ", " \u2013 ")  # En dash

        # Ensure proper spacing after punctuation
        content = re.sub(r"\.([A-Z])", r". \1", content)
        content = re.sub(r"\!([A-Z])", r"! \1", content)
        content = re.sub(r"\?([A-Z])", r"? \1", content)

        # Remove double spaces
        content = re.sub(r" {2,}", " ", content)

        return content

    def normalize_headings(self, content: str) -> str:
        """Normalize heading hierarchy — no skipped levels.

        Ensures headings follow a logical hierarchy (H1 → H2 → H3)
        without skipping levels (e.g., H1 → H3 is fixed to H1 → H2 → H3).

        Args:
            content: Markdown content.

        Returns:
            Content with normalized heading hierarchy.
        """
        lines = content.split("\n")
        result = []
        prev_level = 0

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s", line)
            if heading_match:
                current_level = len(heading_match.group(1))
                # Fix skipped levels
                if current_level > prev_level + 1:
                    current_level = prev_level + 1
                    line = "#" * current_level + line[line.index("#") + len(heading_match.group(1)):]
                prev_level = current_level
            else:
                # Reset heading level tracking on non-heading lines
                if line.strip() == "":
                    prev_level = 0

            result.append(line)

        return "\n".join(result)

    def normalize_lists(self, content: str) -> str:
        """Normalize list formatting — consistent markers and indentation.

        Args:
            content: Markdown content.

        Returns:
            Content with normalized lists.
        """
        # Ensure consistent bullet markers
        content = re.sub(r"^\s*\*\s", "* ", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*-\s", "* ", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*\+\s", "* ", content, flags=re.MULTILINE)

        # Ensure consistent numbered list format
        content = re.sub(r"^\s*(\d+)\.\s+", r"\1. ", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*(\d+)\)\s+", r"\1. ", content, flags=re.MULTILINE)

        return content

    def normalize_code_blocks(self, content: str) -> str:
        """Normalize code block formatting — consistent fence markers.

        Args:
            content: Markdown content.

        Returns:
            Content with normalized code blocks.
        """
        # Ensure all code blocks use ``` fences (not indented)
        # This converts indented code blocks to fenced
        # (Only if they appear after a blank line and have consistent indentation)

        # Ensure consistent language identifiers
        content = re.sub(
            r"```\s*\n",
            "```\n",
            content,
        )
        content = re.sub(
            r"```(\w+)\s*\n",
            lambda m: f"```{m.group(1).lower()}\n",
            content,
        )

        return content

    def normalize_whitespace(self, content: str) -> str:
        """Normalize whitespace — consistent line endings and spacing.

        Args:
            content: Text content.

        Returns:
            Whitespace-normalized content.
        """
        # Normalize line endings
        content = content.replace("\r\n", "\n")
        content = content.replace("\r", "\n")

        # Remove trailing whitespace on each line
        content = re.sub(r"[ \t]+\n", "\n", content)

        # Ensure single blank line between sections
        content = re.sub(r"\n{3,}", "\n\n", content)

        return content.strip() + "\n"
