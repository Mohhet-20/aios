"""Federated identity provider abstraction. `FederatedIdentityProvider`
is the interface every SSO integration implements; `OAuth2Provider` is
a real, generic OAuth2-authorization-code-grant + OIDC-userinfo client
built on `httpx` — since Google, GitHub, Azure AD, and any standards-
compliant OIDC IdP all speak the same three-step dance (authorize
redirect -> code exchange -> userinfo fetch), one configurable
implementation covers all of them; only the URLs, scopes, and userinfo
field names differ per provider (see `registry.py`'s `OAuth2ProviderConfig`).
Callers inject an `httpx.AsyncClient` (real or a `MockTransport`-backed
one in tests), so this performs genuine HTTP calls against whatever
transport it's given rather than fabricating a response."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx

from identity_platform.core.exceptions import FederatedIdentityError
from identity_platform.domain.enums import IdentityProviderKey


@dataclass
class ExternalProfile:
    provider_key: IdentityProviderKey
    external_user_id: str
    email: str | None
    display_name: str | None
    raw_profile: dict = field(default_factory=dict)


class FederatedIdentityProvider(ABC):
    provider_key: IdentityProviderKey

    @abstractmethod
    def build_authorization_url(self, *, state: str, redirect_uri: str) -> str: ...

    @abstractmethod
    async def exchange_code_for_profile(self, *, code: str, redirect_uri: str) -> ExternalProfile: ...


@dataclass
class OAuth2ProviderConfig:
    provider_key: IdentityProviderKey
    authorize_url: str
    token_url: str
    userinfo_url: str
    client_id: str
    client_secret: str
    scope: str = "openid email profile"
    external_id_field: str = "sub"
    email_field: str = "email"
    name_field: str = "name"


class OAuth2Provider(FederatedIdentityProvider):
    def __init__(self, config: OAuth2ProviderConfig, *, http_client: httpx.AsyncClient):
        self.config = config
        self.provider_key = config.provider_key
        self._http = http_client

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.config.client_id, "redirect_uri": redirect_uri, "response_type": "code",
            "scope": self.config.scope, "state": state,
        }
        return f"{self.config.authorize_url}?{urlencode(params)}"

    async def exchange_code_for_profile(self, *, code: str, redirect_uri: str) -> ExternalProfile:
        token_response = await self._http.post(self.config.token_url, data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri,
            "client_id": self.config.client_id, "client_secret": self.config.client_secret,
        })
        if token_response.status_code >= 400:
            raise FederatedIdentityError(f"{self.provider_key.value} token exchange failed: HTTP {token_response.status_code}")
        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            raise FederatedIdentityError(f"{self.provider_key.value} token response did not include an access_token")

        userinfo_response = await self._http.get(
            self.config.userinfo_url, headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_response.status_code >= 400:
            raise FederatedIdentityError(f"{self.provider_key.value} userinfo fetch failed: HTTP {userinfo_response.status_code}")
        profile_payload = userinfo_response.json()

        external_user_id = profile_payload.get(self.config.external_id_field)
        if not external_user_id:
            raise FederatedIdentityError(f"{self.provider_key.value} userinfo response missing '{self.config.external_id_field}'")

        return ExternalProfile(
            provider_key=self.provider_key, external_user_id=str(external_user_id),
            email=profile_payload.get(self.config.email_field), display_name=profile_payload.get(self.config.name_field),
            raw_profile=profile_payload,
        )
