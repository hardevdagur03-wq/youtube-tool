"""Template Engine — reusable branded templates for all export formats.

Supports default, corporate, minimal, academic, and technical templates.
Template variables are injected at render time for consistent branding.
"""

from __future__ import annotations

import logging
from typing import Any

from export_delivery.config import ExportDeliveryConfig
from export_delivery.models import TemplateConfig

logger = logging.getLogger(__name__)


class TemplateEngine:
    """Manages reusable export templates.

    Each template defines brand colors, fonts, spacing, and layout options.
    Templates are applied during export rendering for consistent branding.

    Usage::

        engine = TemplateEngine()
        template = engine.get_template("corporate")
        engine.apply(template, exporter_content)
    """

    def __init__(self, config: ExportDeliveryConfig | None = None) -> None:
        self._config = config or ExportDeliveryConfig.from_env()
        self._templates: dict[str, TemplateConfig] = self._load_defaults()

    def _load_defaults(self) -> dict[str, TemplateConfig]:
        """Load the built-in template collection."""
        return {
            "default": TemplateConfig(
                name="default", label="Default Template",
                description="Standard clean export template",
                brand_color="#059669", secondary_color="#1f2937", accent_color="#7c3aed",
            ),
            "corporate": TemplateConfig(
                name="corporate", label="Corporate Template",
                description="Professional corporate branding",
                brand_color="#2563eb", secondary_color="#1e293b", accent_color="#0891b2",
                font_family="Inter, system-ui, sans-serif",
                font_family_heading="Inter, system-ui, sans-serif",
                cover_page=True, toc_enabled=True,
            ),
            "minimal": TemplateConfig(
                name="minimal", label="Minimal Template",
                description="Clean, minimal design with no frills",
                brand_color="#374151", secondary_color="#111827", accent_color="#4b5563",
                font_family="system-ui, sans-serif",
                cover_page=False, toc_enabled=False,
                header_enabled=False, footer_enabled=False,
            ),
            "academic": TemplateConfig(
                name="academic", label="Academic Template",
                description="Academic paper formatting",
                brand_color="#1e293b", secondary_color="#334155", accent_color="#6366f1",
                font_family="Georgia, 'Times New Roman', serif",
                font_family_heading="Georgia, 'Times New Roman', serif",
                font_size_base=12, line_height=1.8,
                page_size="A4", page_margin_mm=25.4,
                cover_page=True, toc_enabled=True,
            ),
            "technical": TemplateConfig(
                name="technical", label="Technical Template",
                description="Technical documentation format",
                brand_color="#0f172a", secondary_color="#1e293b", accent_color="#0ea5e9",
                font_family="Inter, system-ui, sans-serif",
                font_family_mono="'JetBrains Mono', 'Fira Code', monospace",
                font_size_heading_scale=1.5,
                cover_page=True, toc_enabled=True,
            ),
        }

    def list_templates(self) -> list[dict[str, Any]]:
        """List all available templates.

        Returns:
            List of template summaries.
        """
        return [
            {
                "name": t.name,
                "label": t.label,
                "description": t.description,
            }
            for t in self._templates.values()
        ]

    def get_template(self, name: str) -> TemplateConfig:
        """Get a template by name.

        Args:
            name: Template name (default, corporate, minimal, academic, technical).

        Returns:
            ``TemplateConfig`` with all style settings.
        """
        if name not in self._templates:
            logger.warning("Template '%s' not found, using default", name)
            return self._templates["default"]
        return self._templates[name]

    def register_template(self, config: TemplateConfig) -> None:
        """Register a custom template.

        Args:
            config: Template configuration.
        """
        self._templates[config.name] = config
        logger.info("Template registered: %s (%s)", config.name, config.label)

    def apply_css_variables(self, template_name: str) -> dict[str, str]:
        """Get CSS custom properties for a template.

        Args:
            template_name: Template name.

        Returns:
            Dict of CSS variable name -> value.
        """
        template = self.get_template(template_name)
        return {
            "--brand-color": template.brand_color,
            "--secondary-color": template.secondary_color,
            "--accent-color": template.accent_color,
            "--font-family": template.font_family,
            "--font-family-heading": template.font_family_heading,
            "--font-family-mono": template.font_family_mono,
            "--font-size-base": f"{template.font_size_base}px",
            "--line-height": str(template.line_height),
            **template.css_variables,
        }

    def apply_metadata(self, template_name: str) -> dict[str, str]:
        """Get metadata key-value pairs for a template.

        Args:
            template_name: Template name.

        Returns:
            Dict of metadata key -> value.
        """
        return dict(self.get_template(template_name).template_metadata)

    def render_variables(
        self, content: str, variables: dict[str, Any]
    ) -> str:
        """Replace template variables in content.

        Supports ``{{variable_name}}`` syntax.

        Args:
            content: Template content with variables.
            variables: Dict of variable name -> value.

        Returns:
            Content with variables replaced.
        """
        result = content
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
