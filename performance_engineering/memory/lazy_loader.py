"""Lazy Loader — lazy initialization for expensive resources.

Defers service initialization until first use.
Supports background pre-warming for critical paths.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


class LazyLoader(Generic[T]):
    """Lazy initialization wrapper for expensive resources.

    The wrapped resource is initialized on first access, not at creation time.
    Thread-safe: only initializes once even under concurrent access.

    Usage::

        loader = LazyLoader(ExpensiveService)
        # Service not yet initialized
        service = loader.get()  # Initialized on first access
    """

    def __init__(
        self,
        factory: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._instance: T | None = None
        self._lock = threading.Lock()
        self._initialized = False

    def get(self) -> T:
        """Get or initialize the lazy resource.

        Returns:
            The initialized resource instance.
        """
        if self._initialized and self._instance is not None:
            return self._instance

        with self._lock:
            if not self._initialized:
                logger.debug(
                    "Lazy initializing: %s",
                    self._factory.__name__ if hasattr(self._factory, '__name__') else str(self._factory),
                )
                self._instance = self._factory(*self._args, **self._kwargs)
                self._initialized = True
        return self._instance

    @property
    def is_initialized(self) -> bool:
        """Check if the resource has been initialized."""
        return self._initialized

    def reset(self) -> None:
        """Reset the lazy loader, forcing re-initialization on next get()."""
        with self._lock:
            self._instance = None
            self._initialized = False

    def __call__(self) -> T:
        """Convenience: call the loader to get the instance."""
        return self.get()


class LazyProxy(Generic[T]):
    """Property-like lazy proxy for class attributes.

    Usage::

        class MyService:
            expensive = LazyProxy(ExpensiveResource, "arg1")

        s = MyService()
        # ExpensiveResource not yet created
        result = s.expensive.get()  # Created on first access
    """

    def __init__(self, factory: Callable[..., T], *args: Any, **kwargs: Any) -> None:
        self._loader = LazyLoader(factory, *args, **kwargs)

    def get(self) -> T:
        return self._loader.get()

    @property
    def is_initialized(self) -> bool:
        return self._loader.is_initialized

    def reset(self) -> None:
        self._loader.reset()
