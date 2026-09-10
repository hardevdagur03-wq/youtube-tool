"""Dependency Injection Container.

Wires all layers together using constructor injection.
No service locator anti-pattern — explicit wiring at composition root.
"""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class ServiceRegistry:
    """Simple DI container with lazy service resolution.

    Services are registered as factory functions and resolved on first use.
    Singleton services are cached after first resolution.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Any] = {}
        self._singletons: dict[str, Any] = {}
        self._instances: dict[str, Any] = {}

    def register(self, key: str, factory: Any, singleton: bool = True) -> None:
        self._factories[key] = factory
        self._singletons[key] = singleton

    def register_instance(self, key: str, instance: Any) -> None:
        self._instances[key] = instance
        self._factories[key] = lambda *a, **kw: instance
        self._singletons[key] = True

    def resolve(self, key: str) -> Any:
        if key in self._instances:
            return self._instances[key]

        factory = self._factories.get(key)
        if factory is None:
            raise KeyError(f"Service not registered: {key}")

        is_singleton = self._singletons.get(key, True)

        if is_singleton and key in self._instances:
            return self._instances[key]

        instance = factory(self)
        if is_singleton:
            self._instances[key] = instance
        return instance

    def has(self, key: str) -> bool:
        return key in self._factories or key in self._instances

    def clear(self) -> None:
        self._factories.clear()
        self._singletons.clear()
        self._instances.clear()


container = ServiceRegistry()
