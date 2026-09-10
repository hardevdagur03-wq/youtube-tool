"""Reusable HTTP client with connection pooling, retry, SSL verification,
timeout, comprehensive logging, and user-friendly error handling.

Centralizes all external HTTP communication so that every outbound
request is logged, retried on transient failures, and properly timed out.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, ClassVar

import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class HttpClientError(Exception):
    """Base exception for HTTP client errors."""


class SslHandshakeError(HttpClientError):
    """SSL/TLS handshake failure — server closed connection during handshake."""


class ConnectionTimeoutError(HttpClientError):
    """Connection timed out."""


class HttpUpstreamError(HttpClientError):
    """Upstream server returned an error status."""


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class HttpClientConfig:
    """Configuration for the reusable HTTP client."""
    connect_timeout: float = 15.0
    read_timeout: float = 30.0
    total_timeout: float = 60.0
    max_retries: int = 3
    backoff_factor: float = 1.0
    pool_connections: int = 10
    pool_maxsize: int = 30
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)
    retry_on_methods: frozenset[str] = field(
        default_factory=lambda: frozenset({"HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"})
    )
    ca_bundle_path: str = field(default_factory=lambda: certifi.where())

    @property
    def timeout(self) -> tuple[float, float]:
        return (self.connect_timeout, self.read_timeout)


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

def _redact_headers(headers: dict[str, Any]) -> dict[str, str]:
    """Redact sensitive header values for logging."""
    sensitive = {"authorization", "x-api-key", "api-key", "cookie", "set-cookie"}
    return {
        k: "***" if k.lower() in sensitive else str(v)
        for k, v in headers.items()
    }


# ---------------------------------------------------------------------------
# Reusable HTTP client
# ---------------------------------------------------------------------------

class HttpClient:
    """Reusable HTTP client with connection pooling, retry, and logging.

    Usage::

        client = HttpClient()
        resp = client.get("https://api.example.com/resource")
        data = resp.json()

    All external calls are automatically:
        - Logged before and after (URL, method, elapsed, status)
        - Retried on SSL errors, timeouts, and 5xx statuses
        - Timed out with configurable connect/read timeouts
    """

    _instance: ClassVar["HttpClient | None"] = None
    _config: ClassVar[HttpClientConfig] = HttpClientConfig()

    def __init__(self, config: HttpClientConfig | None = None) -> None:
        if config is not None:
            self._config = config
        self._session = self._build_session()

    @classmethod
    def get_instance(cls, config: HttpClientConfig | None = None) -> "HttpClient":
        """Get or create the singleton HTTP client instance."""
        if cls._instance is None or config is not None:
            cls._instance = cls(config or cls._config)
        return cls._instance

    def _build_session(self) -> requests.Session:
        """Build a requests.Session with retry adapter and SSL config."""
        session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=self._config.max_retries,
            read=self._config.max_retries,
            connect=self._config.max_retries,
            backoff_factor=self._config.backoff_factor,
            status_forcelist=list(self._config.retry_on_status),
            allowed_methods=self._config.retry_on_methods,
            raise_on_status=True,
        )

        adapter = HTTPAdapter(
            pool_connections=self._config.pool_connections,
            pool_maxsize=self._config.pool_maxsize,
            max_retries=retry_strategy,
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Use certifi CA bundle
        session.verify = self._config.ca_bundle_path

        return session

    def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an HTTP request with full logging and error handling.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Request URL.
            **kwargs: Passed to ``requests.Session.request()``.

        Returns:
            ``requests.Response`` on success.

        Raises:
            SslHandshakeError: SSL handshake failed.
            ConnectionTimeoutError: Connection timed out.
            HttpUpstreamError: Server returned an error status.
            HttpClientError: Other HTTP client errors.
        """
        request_id = uuid.uuid4().hex[:8]
        headers = kwargs.pop("headers", {})
        timeout = kwargs.pop("timeout", self._config.timeout)

        log_headers = _redact_headers(headers)
        log_body = kwargs.get("json") or kwargs.get("data")
        if log_body is not None and isinstance(log_body, (dict, list)):
            log_body = str(log_body)[:500]

        logger.info(
            "[%s] >>> %s %s  timeout=%s  headers=%s  body=%s",
            request_id, method.upper(), url, timeout, log_headers,
            log_body if log_body else "-",
        )

        start = time.time()
        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=timeout,
                **kwargs,
            )
            elapsed = round(time.time() - start, 3)
            logger.info(
                "[%s] <<< %s %s  status=%d  elapsed=%.3fs",
                request_id, method.upper(), url, response.status_code, elapsed,
            )
            response.raise_for_status()
            return response

        except requests.exceptions.SSLError as exc:
            elapsed = round(time.time() - start, 3)
            logger.error(
                "[%s] SSL HANDSHAKE FAILED %s %s  elapsed=%.3fs  error=%s",
                request_id, method.upper(), url, elapsed, exc,
            )
            raise SslHandshakeError(
                "Unable to connect securely to the service. "
                "The server closed the connection during the SSL/TLS handshake. "
                "This may be due to network interference, a proxy, or an incompatible TLS version."
            ) from exc

        except requests.exceptions.ConnectionError as exc:
            elapsed = round(time.time() - start, 3)
            logger.error(
                "[%s] CONNECTION FAILED %s %s  elapsed=%.3fs  error=%s",
                request_id, method.upper(), url, elapsed, exc,
            )
            raise ConnectionTimeoutError(
                "Unable to connect to the service. "
                "Please check your network connection and try again."
            ) from exc

        except requests.exceptions.Timeout as exc:
            elapsed = round(time.time() - start, 3)
            logger.error(
                "[%s] TIMEOUT %s %s  elapsed=%.3fs  error=%s",
                request_id, method.upper(), url, elapsed, exc,
            )
            raise ConnectionTimeoutError(
                "The connection timed out. Please try again in a few moments."
            ) from exc

        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            elapsed = round(time.time() - start, 3)
            logger.error(
                "[%s] HTTP ERROR %s %s  status=%d  elapsed=%.3fs  error=%s",
                request_id, method.upper(), url, status, elapsed, exc,
            )
            raise HttpUpstreamError(
                f"The service returned an error (HTTP {status}). "
                "Please try again later."
            ) from exc

        except Exception as exc:
            elapsed = round(time.time() - start, 3)
            logger.exception(
                "[%s] UNEXPECTED ERROR %s %s  elapsed=%.3fs",
                request_id, method.upper(), url, elapsed,
            )
            raise HttpClientError(
                "An unexpected error occurred while connecting to the service. "
                "Technical details have been logged."
            ) from exc

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        """Close the underlying session and free resources."""
        self._session.close()
        logger.debug("HTTP client session closed")

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
