import httpx
import pytest

from identity_platform.core.exceptions import FederatedIdentityError, UnknownIdentityProviderError
from identity_platform.domain.enums import IdentityProviderKey
from identity_platform.federated.provider import OAuth2Provider, OAuth2ProviderConfig
from identity_platform.federated.registry import ProviderRegistry
from identity_platform.federated.saml_provider import SamlProvider, SamlProviderConfig


def _config(**overrides) -> OAuth2ProviderConfig:
    defaults = dict(
        provider_key=IdentityProviderKey.GOOGLE, authorize_url="https://idp.example.com/authorize",
        token_url="https://idp.example.com/token", userinfo_url="https://idp.example.com/userinfo",
        client_id="client-123", client_secret="secret-456",
    )
    defaults.update(overrides)
    return OAuth2ProviderConfig(**defaults)


def _mock_transport(*, token_status=200, userinfo_status=200, userinfo_payload=None):
    userinfo_payload = userinfo_payload if userinfo_payload is not None else {
        "sub": "google-user-1", "email": "alice@example.com", "name": "Alice Example",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/token":
            if token_status >= 400:
                return httpx.Response(token_status, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "fake-access-token", "token_type": "Bearer"})
        if request.url.path == "/userinfo":
            assert request.headers["authorization"] == "Bearer fake-access-token"
            if userinfo_status >= 400:
                return httpx.Response(userinfo_status, json={"error": "invalid_token"})
            return httpx.Response(200, json=userinfo_payload)
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_build_authorization_url_includes_client_and_scope():
    provider = OAuth2Provider(_config(), http_client=httpx.AsyncClient(trust_env=False))
    url = provider.build_authorization_url(state="xyz", redirect_uri="https://app.example.com/callback")
    assert "client_id=client-123" in url
    assert "state=xyz" in url
    assert url.startswith("https://idp.example.com/authorize?")


@pytest.mark.asyncio
async def test_exchange_code_for_profile_success():
    async with httpx.AsyncClient(transport=_mock_transport()) as client:
        provider = OAuth2Provider(_config(), http_client=client)
        profile = await provider.exchange_code_for_profile(code="auth-code", redirect_uri="https://app.example.com/callback")

    assert profile.provider_key == IdentityProviderKey.GOOGLE
    assert profile.external_user_id == "google-user-1"
    assert profile.email == "alice@example.com"
    assert profile.display_name == "Alice Example"


@pytest.mark.asyncio
async def test_exchange_code_for_profile_raises_on_token_error():
    async with httpx.AsyncClient(transport=_mock_transport(token_status=401)) as client:
        provider = OAuth2Provider(_config(), http_client=client)
        with pytest.raises(FederatedIdentityError):
            await provider.exchange_code_for_profile(code="bad-code", redirect_uri="https://app.example.com/callback")


@pytest.mark.asyncio
async def test_exchange_code_for_profile_raises_on_userinfo_error():
    async with httpx.AsyncClient(transport=_mock_transport(userinfo_status=403)) as client:
        provider = OAuth2Provider(_config(), http_client=client)
        with pytest.raises(FederatedIdentityError):
            await provider.exchange_code_for_profile(code="auth-code", redirect_uri="https://app.example.com/callback")


@pytest.mark.asyncio
async def test_exchange_code_for_profile_raises_when_external_id_missing():
    async with httpx.AsyncClient(transport=_mock_transport(userinfo_payload={"email": "no-sub@example.com"})) as client:
        provider = OAuth2Provider(_config(), http_client=client)
        with pytest.raises(FederatedIdentityError):
            await provider.exchange_code_for_profile(code="auth-code", redirect_uri="https://app.example.com/callback")


def test_provider_registry_register_and_get():
    registry = ProviderRegistry()
    provider = OAuth2Provider(_config(), http_client=httpx.AsyncClient(trust_env=False))
    registry.register(provider)

    assert registry.get(IdentityProviderKey.GOOGLE) is provider
    assert IdentityProviderKey.GOOGLE in registry.list_registered()


def test_provider_registry_raises_for_unregistered_provider():
    registry = ProviderRegistry()
    with pytest.raises(UnknownIdentityProviderError):
        registry.get(IdentityProviderKey.GITHUB)


def test_saml_authorization_url_contains_relay_state():
    saml = SamlProvider(SamlProviderConfig(
        idp_entity_id="idp", idp_sso_url="https://idp.example.com/sso",
        sp_entity_id="sp", acs_url="https://app.example.com/acs",
    ))
    url = saml.build_authorization_url(state="relay-1", redirect_uri="https://app.example.com/acs")
    assert "RelayState=relay-1" in url


@pytest.mark.asyncio
async def test_saml_exchange_code_not_implemented():
    saml = SamlProvider(SamlProviderConfig(
        idp_entity_id="idp", idp_sso_url="https://idp.example.com/sso",
        sp_entity_id="sp", acs_url="https://app.example.com/acs",
    ))
    with pytest.raises(NotImplementedError):
        await saml.exchange_code_for_profile(code="n/a", redirect_uri="https://app.example.com/acs")
