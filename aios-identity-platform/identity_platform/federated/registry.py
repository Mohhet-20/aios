"""ProviderRegistry: in-memory map from `IdentityProviderKey` to a
configured `FederatedIdentityProvider` instance. Providers are
registered explicitly (rather than auto-constructed from env vars)
because each organization may configure its own client_id/secret for
enterprise IdPs — a future multi-tenant config layer (Task 142) reads
per-organization settings and calls `register` per request; this
registry itself is deliberately tenant-agnostic."""
from __future__ import annotations

from identity_platform.core.exceptions import UnknownIdentityProviderError
from identity_platform.domain.enums import IdentityProviderKey
from identity_platform.federated.provider import FederatedIdentityProvider


class ProviderRegistry:
    def __init__(self):
        self._providers: dict[IdentityProviderKey, FederatedIdentityProvider] = {}

    def register(self, provider: FederatedIdentityProvider) -> None:
        self._providers[provider.provider_key] = provider

    def get(self, provider_key: IdentityProviderKey) -> FederatedIdentityProvider:
        provider = self._providers.get(provider_key)
        if provider is None:
            raise UnknownIdentityProviderError(f"no provider registered for '{provider_key.value}'")
        return provider

    def list_registered(self) -> list[IdentityProviderKey]:
        return list(self._providers.keys())
