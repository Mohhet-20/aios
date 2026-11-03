"""WebhookSecretService: the HMAC signing secret this platform uses to
sign *outbound* webhook payloads so a receiver can verify authenticity
(the same scheme Stripe/GitHub webhooks use — `X-Signature: HMAC-SHA256
(secret, raw_body)`). This is deliberately the one credential in the
platform that is NOT one-way hashed: since the platform itself must
resign a fresh payload on every outbound delivery (not just verify
once at issuance), the secret has to be recoverable, so it is Fernet-
encrypted at rest via `security/encryption.py` — the same "genuinely
reversible when the use case requires it" pattern the Tool Platform's
Credential Vault and this platform's own TOTP secrets use.
`WebhookSecretModel.secret_hash` holds that ciphertext, not a one-way
digest; the raw secret is also returned once at issuance/rotation for
the caller to keep as a reference if they need to configure a matching
verifier."""
from __future__ import annotations

import hashlib
import hmac

from identity_platform.database.base import utcnow
from identity_platform.models.api_key import WebhookSecretModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.encryption import SecretsEncryptor, get_default_encryptor
from identity_platform.security.tokens import generate_raw_token


def sign_payload(raw_secret: str, payload: bytes) -> str:
    return hmac.new(raw_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_signature(raw_secret: str, payload: bytes, signature: str) -> bool:
    expected = sign_payload(raw_secret, payload)
    return hmac.compare_digest(expected, signature)


class WebhookSecretService:
    def __init__(self, repos: RepositoryRegistry, *, encryptor: SecretsEncryptor | None = None):
        self.repos = repos
        self._encryptor = encryptor or get_default_encryptor()

    async def create_secret(self, organization_id: str, *, name: str) -> tuple[WebhookSecretModel, str]:
        await self.repos.organizations.get_or_404(organization_id)
        raw_secret = generate_raw_token()
        secret = WebhookSecretModel(organization_id=organization_id, name=name, secret_hash=self._encryptor.encrypt(raw_secret))
        await self.repos.webhook_secrets.add(secret)
        return secret, raw_secret

    async def rotate_secret(self, secret_id: str) -> tuple[WebhookSecretModel, str]:
        secret = await self.repos.webhook_secrets.get_or_404(secret_id)
        raw_secret = generate_raw_token()
        secret.secret_hash = self._encryptor.encrypt(raw_secret)
        secret.rotated_at = utcnow()
        await self.repos.webhook_secrets.update(secret)
        return secret, raw_secret

    async def sign_outbound_payload(self, secret_id: str, payload: bytes) -> str:
        secret = await self.repos.webhook_secrets.get_or_404(secret_id)
        raw_secret = self._encryptor.decrypt(secret.secret_hash)
        return sign_payload(raw_secret, payload)

    async def list_for_organization(self, organization_id: str) -> list[WebhookSecretModel]:
        return await self.repos.webhook_secrets.list_for_organization(organization_id)
