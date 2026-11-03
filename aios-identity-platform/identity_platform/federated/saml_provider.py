"""SAML 2.0 integration surface. A real SAML Service Provider needs XML
canonicalization, XML-DSig signature verification, and assertion
encryption — correctly and securely implementing that from stdlib
alone would be a security liability (this is exactly the kind of
crypto primitive that should come from an audited library, e.g.
`python3-saml`, not be reimplemented), and no such dependency was
added to this platform. `SamlProvider` therefore defines the
integration contract — metadata generation and mapping a
already-validated assertion's attributes to an `ExternalProfile` — so
that wiring in a real SAML toolkit later is a matter of implementing
`parse_and_validate_response` against that library, without touching
`FederatedIdentityService` or any caller. Calling `parse_and_validate_response`
today raises `NotImplementedError` rather than silently accepting an
unverified assertion."""
from __future__ import annotations

from dataclasses import dataclass

from identity_platform.domain.enums import IdentityProviderKey
from identity_platform.federated.provider import ExternalProfile, FederatedIdentityProvider


@dataclass
class SamlProviderConfig:
    idp_entity_id: str
    idp_sso_url: str
    sp_entity_id: str
    acs_url: str
    name_id_field: str = "email"
    display_name_attribute: str = "displayName"


class SamlProvider(FederatedIdentityProvider):
    provider_key = IdentityProviderKey.SAML

    def __init__(self, config: SamlProviderConfig):
        self.config = config

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> str:
        """Returns the IdP-initiated SSO URL; a real implementation
        would embed a signed `AuthnRequest` (base64 + deflate) as the
        `SAMLRequest` query parameter."""
        return f"{self.config.idp_sso_url}?SPEntityID={self.config.sp_entity_id}&RelayState={state}"

    async def exchange_code_for_profile(self, *, code: str, redirect_uri: str) -> ExternalProfile:
        raise NotImplementedError(
            "SAML assertion exchange is not a code exchange (see parse_and_validate_response); "
            "SAML support requires a dedicated SAML toolkit for signature verification."
        )

    def parse_and_validate_response(self, saml_response_xml: str) -> ExternalProfile:
        raise NotImplementedError(
            "Real SAML response parsing requires XML-DSig signature verification via an "
            "audited SAML toolkit (e.g. python3-saml) — not implemented in this platform yet."
        )
