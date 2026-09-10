"""Connection Pool Manager — centralized connection pooling for all external services.

Manages HTTP/HTTPS connection pools for YouTube API, OpenAI, Gemini, Deepgram,
AssemblyAI, Redis, and Database. Reuses connections to prevent connection storms.
"""

from __future__ import annotations

import logging
from typing import Any

from performance_engineering.config import PerformanceConfig

logger = logging.getLogger(__name__)

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


class ConnectionPoolManager:
    """Centralized connection pool management.

    Provides shared connection pools for all external services.
    Reuses connections to prevent connection storms and reduce latency.

    Usage::

        pool = ConnectionPoolManager()
        client = pool.get_http_client()
        response = await client.get("https://api.youtube.com/...")
    """

    def __init__(self, config: PerformanceConfig | None = None) -> None:
        self._config = config or PerformanceConfig.from_env()
        self._http_clients: dict[str, httpx.AsyncClient] = {}
        self._pool_stats: dict[str, dict[str, Any]] = {}

    def get_http_client(
        self,
        service_name: str = "default",
        base_url: str | None = None,
        timeout: float = 30.0,
        max_connections: int | None = None,
    ) -> Any:
        """Get or create an HTTP client for a service.

        Args:
            service_name: Service identifier for pool reuse.
            base_url: Optional base URL for the client.
            timeout: Request timeout in seconds.
            max_connections: Max connections in pool.

        Returns:
            An httpx.AsyncClient instance.
        """
        if service_name in self._http_clients:
            return self._http_clients[service_name]

        if not _HAS_HTTPX:
            logger.warning("httpx not installed, returning None for %s", service_name)
            return None

        max_conn = max_connections or self._config.pool_http_max_connections
        limits = httpx.Limits(
            max_connections=max_conn,
            max_keepalive_connections=min(max_conn, self._config.pool_http_max_keepalive),
        )

        client_kwargs: dict[str, Any] = {
            "limits": limits,
            "timeout": httpx.Timeout(timeout, connect=10.0, read=timeout),
        }
        if base_url:
            client_kwargs["base_url"] = base_url

        client = httpx.AsyncClient(**client_kwargs)
        self._http_clients[service_name] = client

        self._pool_stats[service_name] = {
            "created_at": __import__("time").time(),
            "max_connections": max_conn,
            "base_url": base_url,
            "requests": 0,
        }

        logger.debug(
            "HTTP client created: %s (max_conn=%d, base=%s)",
            service_name, max_conn, base_url or "none",
        )

        return client

    def get_youtube_client(self) -> Any:
        """Get a shared YouTube Data API client."""
        return self.get_http_client(
            "youtube",
            base_url="https://www.googleapis.com/youtube/v3",
            timeout=15.0,
        )

    def get_openai_client(self) -> Any:
        """Get a shared OpenAI API client."""
        return self.get_http_client(
            "openai",
            base_url="https://api.openai.com/v1",
            timeout=60.0,
        )

    def get_gemini_client(self) -> Any:
        """Get a shared Google Gemini API client."""
        return self.get_http_client(
            "gemini",
            base_url="https://generativelanguage.googleapis.com/v1",
            timeout=60.0,
        )

    def get_deepgram_client(self) -> Any:
        """Get a shared Deepgram API client."""
        return self.get_http_client(
            "deepgram",
            base_url="https://api.deepgram.com/v1",
            timeout=120.0,
        )

    def get_assemblyai_client(self) -> Any:
        """Get a shared AssemblyAI API client."""
        return self.get_http_client(
            "assemblyai",
            base_url="https://api.assemblyai.com/v2",
            timeout=120.0,
        )

    def record_request(self, service_name: str) -> None:
        """Record a request made through a pool.

        Args:
            service_name: Service identifier.
        """
        if service_name in self._pool_stats:
            self._pool_stats[service_name]["requests"] += 1

    def get_stats(self) -> dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            Dict with per-pool stats and overall summary.
        """
        total_requests = sum(
            s["requests"] for s in self._pool_stats.values()
        )
        return {
            "pools": {
                name: {
                    "requests": stats["requests"],
                    "max_connections": stats["max_connections"],
                    "age_seconds": round(
                        __import__("time").time() - stats["created_at"], 1
                    ),
                }
                for name, stats in self._pool_stats.items()
            },
            "total_pools": len(self._pool_stats),
            "total_requests": total_requests,
            "active_clients": len(self._http_clients),
        }

    async def close_all(self) -> None:
        """Close all HTTP client connections."""
        for name, client in self._http_clients.items():
            try:
                await client.aclose()
                logger.debug("Closed HTTP client: %s", name)
            except Exception as exc:
                logger.warning("Error closing HTTP client %s: %s", name, exc)
        self._http_clients.clear()
        logger.info("All HTTP clients closed")

    async def close(self, service_name: str) -> None:
        """Close a specific HTTP client.

        Args:
            service_name: Service identifier.
        """
        client = self._http_clients.pop(service_name, None)
        if client:
            try:
                await client.aclose()
            except Exception as exc:
                logger.warning("Error closing %s: %s", service_name, exc)
