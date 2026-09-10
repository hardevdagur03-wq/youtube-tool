"""Export Router — format selection and exporter dispatch.

Maps format keys to exporter implementations.
Handles format dependency resolution and scheduling.
"""

from __future__ import annotations

import logging
from typing import Any

from export_delivery.config import ExportDeliveryConfig
from export_delivery.constants import FORMATS

logger = logging.getLogger(__name__)


class ExportRouter:
    """Routes export format selection to the correct exporter.

    Maintains a registry of available exporters and maps format keys
    to their implementations.
    """

    def __init__(self, config: ExportDeliveryConfig | None = None) -> None:
        self._config = config or ExportDeliveryConfig.from_env()
        self._exporters: dict[str, Any] = {}

    def register(self, format_key: str, exporter_instance: Any) -> None:
        """Register an exporter for a format key.

        Args:
            format_key: Format key (e.g. 'markdown', 'html').
            exporter_instance: Exporter instance with export() method.
        """
        self._exporters[format_key] = exporter_instance
        logger.debug("Exporter registered: %s", format_key)

    def select_exporter(self, format_key: str) -> Any | None:
        """Get the exporter for a format key.

        Args:
            format_key: Format key.

        Returns:
            Exporter instance or None if not registered.
        """
        return self._exporters.get(format_key)

    def get_format_info(self, format_key: str) -> dict[str, Any] | None:
        """Get metadata about a format.

        Args:
            format_key: Format key.

        Returns:
            Format info dict or None.
        """
        return FORMATS.get(format_key)

    def list_supported_formats(self) -> list[dict[str, Any]]:
        """List all supported formats with metadata.

        Returns:
            List of format info dicts.
        """
        return [
            {"key": key, **info}
            for key, info in FORMATS.items()
            if key in self._config.formats_enabled
        ]

    def get_registered_formats(self) -> list[str]:
        """List formats that have registered exporters.

        Returns:
            List of format keys.
        """
        return list(self._exporters.keys())

    def is_format_supported(self, format_key: str) -> bool:
        """Check if a format is supported.

        Args:
            format_key: Format key.

        Returns:
            True if supported and has a registered exporter.
        """
        return format_key in FORMATS and format_key in self._exporters
