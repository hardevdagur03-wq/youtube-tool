from __future__ import annotations

import re
import time
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from security.security_models import (
    AuthenticationError, AuthorizationError, InvalidTokenError,
    RateLimitError, SecurityError, ThreatDetectedError, TokenExpiredError,
)
from security.security_headers import SecurityHeadersMiddleware


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        auth_manager: Any,
        rate_limiter: Any | None = None,
        input_validator: Any | None = None,
        audit_logger: Any | None = None,
        excluded_paths: list[str] | None = None,
    ):
        super().__init__(app)
        self._auth = auth_manager
        self._rate_limiter = rate_limiter
        self._input_validator = input_validator
        self._audit_logger = audit_logger
        self._excluded = excluded_paths or [
            r"^/health$",
            r"^/metrics$",
            r"^/docs$",
            r"^/redoc$",
            r"^/openapi\.json$",
            r"^/api/v1/auth/login$",
            r"^/api/v1/auth/register$",
            r"^/api/v1/auth/refresh$",
            r"^/api/v1/auth/oauth/.*$",
        ]

    def _is_excluded(self, path: str) -> bool:
        for pattern in self._excluded:
            if re.match(pattern, path):
                return True
        return False

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._is_excluded(request.url.path):
            return await call_next(request)

        try:
            if self._rate_limiter:
                self._rate_limiter.check(f"api:{request.client.host if request.client else 'unknown'}")

            auth_header = request.headers.get("Authorization", "")
            user = None

            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                user = self._auth.verify_token(token)
            elif auth_header.startswith("ApiKey "):
                apikey = auth_header[7:]
                result = self._auth.authenticate_with_api_key(apikey)
                user = result.get("user")

            if user:
                request.state.user = user
            else:
                request.state.user = None

        except TokenExpiredError:
            return JSONResponse(status_code=401, content={"detail": "Token expired"})
        except InvalidTokenError:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        except AuthenticationError:
            return JSONResponse(status_code=401, content={"detail": "Authentication failed"})
        except RateLimitError:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        except SecurityError as e:
            return JSONResponse(status_code=403, content={"detail": str(e)})

        try:
            response = await call_next(request)
            return response
        except SecurityError as e:
            return JSONResponse(status_code=403, content={"detail": str(e)})
