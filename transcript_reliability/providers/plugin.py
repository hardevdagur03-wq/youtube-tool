"""Plugin System — auto-discovery of provider plugins.

Scans the providers/plugins/ directory for additional provider implementations.
New providers can be added by dropping a Python file into the plugins directory
without modifying any core code.
"""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from typing import Any

from transcript_reliability.interfaces.provider import TranscriptProvider

logger = logging.getLogger(__name__)

# Path to the plugins directory
_PLUGINS_DIR = os.path.join(os.path.dirname(__file__), "plugins")


def discover_plugins() -> list[TranscriptProvider]:
    """Auto-discover provider plugins from the plugins directory.

    Scans ``transcript_reliability/providers/plugins/`` for Python files,
    imports them, and collects all ``TranscriptProvider`` subclasses.

    Returns:
        List of instantiated provider plugin instances.
    """
    providers: list[TranscriptProvider] = []

    if not os.path.isdir(_PLUGINS_DIR):
        return providers

    for entry in os.listdir(_PLUGINS_DIR):
        if entry.startswith("_") or not entry.endswith(".py"):
            continue
        module_name = entry[:-3]
        try:
            module = importlib.import_module(
                f"transcript_reliability.providers.plugins.{module_name}"
            )
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, TranscriptProvider)
                    and attr is not TranscriptProvider
                ):
                    try:
                        instance = attr()
                        providers.append(instance)
                        logger.info(
                            "Discovered plugin provider: %s (%s)",
                            instance.provider_id, instance.name,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Failed to instantiate plugin %s.%s: %s",
                            module_name, attr_name, exc,
                        )
        except Exception as exc:
            logger.warning("Failed to load plugin module '%s': %s", module_name, exc)

    return providers


def register_external_provider(provider_class: type) -> TranscriptProvider:
    """Register an external provider class at runtime.

    Args:
        provider_class: A class implementing TranscriptProvider.

    Returns:
        The instantiated provider.
    """
    if not isinstance(provider_class, type) or not issubclass(provider_class, TranscriptProvider):
        raise TypeError(
            f"Expected a TranscriptProvider subclass, got {provider_class}"
        )

    instance = provider_class()
    logger.info("Registered external provider: %s (%s)", instance.provider_id, instance.name)
    return instance
