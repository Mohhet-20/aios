import pytest

from identity_platform.api_keys.webhook_secret_service import WebhookSecretService, sign_payload, verify_signature
from identity_platform.domain.enums import UserStatus
from identity_platform.models.user import UserModel
from identity_platform.organizations.organization_service import OrganizationService


async def _make_org(repos, db_session, name: str, email: str):
    owner = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(owner)
    await db_session.commit()
    org = await OrganizationService(repos).create_organization(name=name, owner_user_id=owner.id)
    await db_session.commit()
    return org, owner


def test_sign_and_verify_payload_roundtrip():
    signature = sign_payload("my-secret", b'{"event": "ping"}')
    assert verify_signature("my-secret", b'{"event": "ping"}', signature)
    assert not verify_signature("my-secret", b'{"event": "pong"}', signature)
    assert not verify_signature("wrong-secret", b'{"event": "ping"}', signature)


@pytest.mark.asyncio
async def test_create_secret_and_sign_outbound_payload(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Webhook Co", "webhook-owner@example.com")
    service = WebhookSecretService(repos)

    secret, raw_secret = await service.create_secret(org.id, name="Primary Webhook Secret")
    await db_session.commit()
    assert secret.secret_hash != raw_secret  # stored ciphertext, not the raw secret

    payload = b'{"event": "user.created"}'
    signature = await service.sign_outbound_payload(secret.id, payload)
    assert verify_signature(raw_secret, payload, signature)


@pytest.mark.asyncio
async def test_rotate_secret_changes_signature(repos, db_session):
    org, _ = await _make_org(repos, db_session, "Rotate Webhook Co", "rotate-webhook-owner@example.com")
    service = WebhookSecretService(repos)
    secret, raw_secret_before = await service.create_secret(org.id, name="Rotating Secret")
    await db_session.commit()

    rotated, raw_secret_after = await service.rotate_secret(secret.id)
    await db_session.commit()
    assert raw_secret_after != raw_secret_before
    assert rotated.rotated_at is not None

    payload = b"payload"
    signature = await service.sign_outbound_payload(secret.id, payload)
    assert verify_signature(raw_secret_after, payload, signature)
    assert not verify_signature(raw_secret_before, payload, signature)


@pytest.mark.asyncio
async def test_list_secrets_for_organization(repos, db_session):
    org, _ = await _make_org(repos, db_session, "List Webhook Co", "list-webhook-owner@example.com")
    service = WebhookSecretService(repos)
    await service.create_secret(org.id, name="Secret A")
    await service.create_secret(org.id, name="Secret B")
    await db_session.commit()

    secrets = await service.list_for_organization(org.id)
    assert len(secrets) == 2
