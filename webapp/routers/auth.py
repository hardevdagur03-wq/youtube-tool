"""Authentication and authorization API routes.

Thin controller layer — delegates all business logic to AuthService.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from database.base import utcnow
from database.models import UserModel
from database.repositories.base import BaseRepository
from database.session import get_db_session
from models.api_response import error_response, success_response
from security.jwt_service import JWTService
from security.oauth_service import OAuthService
from security.security_models import TokenExpiredError
from services.iam.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service(request: Request) -> AuthService:
    if not hasattr(request.app.state, "auth_service"):
        user_repo = BaseRepository(UserModel)
        jwt_service = JWTService()
        oauth_service = OAuthService()
        request.app.state.auth_service = AuthService(user_repo, jwt_service, oauth_service)
    return request.app.state.auth_service


@router.post("/register")
async def register(
    request: Request,
    body: dict[str, Any],
    auth: AuthService = Depends(get_auth_service),
):
    email = body.get("email", "")
    password = body.get("password", "")
    username = body.get("username", "")

    if not email or not password:
        return error_response(
            message="Email and password required",
            status_code=400,
            error_code="VALIDATION_ERROR",
        )

    result = await auth.register(
        email=email,
        password=password,
        username=username or email.split("@")[0],
        display_name=body.get("display_name", ""),
    )

    if not result.success:
        return error_response(
            message=result.error,
            status_code=409 if result.error_code == "EMAIL_EXISTS" else 400,
            error_code=result.error_code,
        )

    return success_response(
        data={
            "user": {
                "uuid": result.user.uuid,
                "email": result.user.email,
                "username": result.user.username,
            },
            "tokens": {
                "access_token": result.tokens.access_token,
                "refresh_token": result.tokens.refresh_token,
                "expires_in": result.tokens.expires_in,
                "token_type": result.tokens.token_type,
            },
        },
        message="Registration successful",
    )


@router.post("/login")
async def login(
    request: Request,
    body: dict[str, Any],
    auth: AuthService = Depends(get_auth_service),
):
    email = body.get("email", "")
    password = body.get("password", "")

    if not email or not password:
        return error_response(
            message="Email and password required",
            status_code=400,
            error_code="VALIDATION_ERROR",
        )

    result = await auth.login(email=email, password=password)

    if not result.success:
        status = 401 if result.error_code == "INVALID_CREDENTIALS" else 403
        return error_response(
            message=result.error,
            status_code=status,
            error_code=result.error_code,
        )

    return success_response(
        data={
            "user": {
                "uuid": result.user.uuid,
                "email": result.user.email,
                "username": result.user.username,
            },
            "tokens": {
                "access_token": result.tokens.access_token,
                "refresh_token": result.tokens.refresh_token,
                "expires_in": result.tokens.expires_in,
                "token_type": result.tokens.token_type,
            },
        },
        message="Login successful",
    )


@router.post("/refresh")
async def refresh_token(
    request: Request,
    body: dict[str, Any],
    auth: AuthService = Depends(get_auth_service),
):
    refresh_token = body.get("refresh_token", "")

    if not refresh_token:
        return error_response(
            message="Refresh token required",
            status_code=400,
            error_code="VALIDATION_ERROR",
        )

    result = auth.refresh_access_token(refresh_token)

    if not result.success:
        status = 401 if result.error_code == "TOKEN_EXPIRED" else 401
        return error_response(
            message=result.error,
            status_code=status,
            error_code=result.error_code,
        )

    return success_response(
        data={
            "access_token": result.tokens.access_token,
            "refresh_token": result.tokens.refresh_token,
            "expires_in": result.tokens.expires_in,
            "token_type": result.tokens.token_type,
        },
        message="Token refreshed",
    )


@router.get("/me")
async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return error_response(
            message="Missing or invalid Authorization header",
            status_code=401,
            error_code="AUTH_REQUIRED",
        )

    token = auth_header.split(" ", 1)[1]
    auth_service = get_auth_service(request)

    try:
        claims = auth_service.validate_access_token(token)
    except TokenExpiredError:
        return error_response(
            message="Token expired",
            status_code=401,
            error_code="TOKEN_EXPIRED",
        )
    except Exception:
        return error_response(
            message="Invalid token",
            status_code=401,
            error_code="INVALID_TOKEN",
        )

    return success_response(
        data={
            "sub": claims.get("sub", ""),
            "email": claims.get("email", ""),
            "role": claims.get("role", ""),
        },
        message="Token valid",
    )


@router.post("/logout")
async def logout(request: Request):
    return success_response(message="Logged out successfully")
