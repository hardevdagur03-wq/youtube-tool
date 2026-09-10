from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx

from security.security_models import AuthProvider, AuthenticationError, User


@dataclass
class OAuthProviderConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    scopes: list[str] = field(default_factory=list)


class OAuthProvider:
    def __init__(self, config: OAuthProviderConfig):
        self._config = config

    def get_authorize_url(self, state: str) -> str:
        params = {
            "client_id": self._config.client_id,
            "redirect_uri": self._config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._config.scopes),
            "state": state,
        }
        return f"{self._config.authorize_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._config.token_url,
                data={
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "code": code,
                    "redirect_uri": self._config.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                raise AuthenticationError(f"OAuth token exchange failed: {resp.text}")
            return resp.json()

    async def get_userinfo(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self._config.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                raise AuthenticationError(f"OAuth userinfo failed: {resp.text}")
            return resp.json()


class OAuthService:
    def __init__(self):
        self._providers: dict[str, OAuthProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        google = OAuthProviderConfig(
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/google/callback"),
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
            scopes=["openid", "email", "profile"],
        )
        if google.client_id:
            self._providers["google"] = OAuthProvider(google)

        github = OAuthProviderConfig(
            client_id=os.getenv("GITHUB_OAUTH_CLIENT_ID", ""),
            client_secret=os.getenv("GITHUB_OAUTH_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/github/callback"),
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scopes=["read:user", "user:email"],
        )
        if github.client_id:
            self._providers["github"] = OAuthProvider(github)

        microsoft = OAuthProviderConfig(
            client_id=os.getenv("MICROSOFT_OAUTH_CLIENT_ID", ""),
            client_secret=os.getenv("MICROSOFT_OAUTH_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("MICROSOFT_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/microsoft/callback"),
            authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
            userinfo_url="https://graph.microsoft.com/v1.0/me",
            scopes=["openid", "email", "profile", "User.Read"],
        )
        if microsoft.client_id:
            self._providers["microsoft"] = OAuthProvider(microsoft)

    def get_provider(self, name: str) -> OAuthProvider | None:
        return self._providers.get(name)

    def get_authorize_url(self, provider: str, state: str) -> str:
        oauth = self.get_provider(provider)
        if not oauth:
            raise AuthenticationError(f"Unknown OAuth provider: {provider}")
        return oauth.get_authorize_url(state)

    async def authenticate(self, provider: str, code: str) -> User:
        oauth = self.get_provider(provider)
        if not oauth:
            raise AuthenticationError(f"Unknown OAuth provider: {provider}")
        token_data = await oauth.exchange_code(code)
        access_token = token_data.get("access_token", "")
        userinfo = await oauth.get_userinfo(access_token)
        if provider == "google":
            return self._google_user(userinfo)
        elif provider == "github":
            return self._github_user(userinfo)
        elif provider == "microsoft":
            return self._microsoft_user(userinfo)
        raise AuthenticationError(f"Unsupported provider: {provider}")

    def _google_user(self, info: dict[str, Any]) -> User:
        return User(
            id=f"google_{info.get('id', '')}",
            email=info.get("email", ""),
            username=info.get("name", info.get("email", "")),
        )

    def _github_user(self, info: dict[str, Any]) -> User:
        return User(
            id=f"github_{info.get('id', '')}",
            email=info.get("email", "") or f"{info.get('login', '')}@github.com",
            username=info.get("login", ""),
        )

    def _microsoft_user(self, info: dict[str, Any]) -> User:
        return User(
            id=f"microsoft_{info.get('id', '')}",
            email=info.get("mail", info.get("userPrincipalName", "")),
            username=info.get("displayName", info.get("userPrincipalName", "")),
        )
