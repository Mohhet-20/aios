"""MfaService: TOTP enrollment/verification plus recovery-code issuance
and redemption. The TOTP shared secret is Fernet-encrypted at rest
(`security/encryption.py`) since — unlike a password or token — it
must be decrypted again on every login to compute the expected code;
recovery codes, by contrast, are one-way hashed exactly like every
other single-use token in this platform, since they are only ever
compared, never decrypted."""
from __future__ import annotations

from dataclasses import dataclass

from identity_platform.config.settings import Settings, get_settings
from identity_platform.core.exceptions import (
    ConflictError,
    InvalidMfaCodeError,
    RecoveryCodeExhaustedError,
)
from identity_platform.database.base import utcnow
from identity_platform.domain.enums import MfaFactorStatus, MfaFactorType
from identity_platform.mfa.mappers import apply_mfa_factor_domain_to_model, mfa_factor_to_domain
from identity_platform.models.mfa import MfaFactorModel, RecoveryCodeModel
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security.encryption import SecretsEncryptor, get_default_encryptor
from identity_platform.security.tokens import generate_raw_token, hash_token
from identity_platform.security.totp import generate_totp_secret, provisioning_uri, verify_totp


@dataclass
class EnrollmentResult:
    factor_id: str
    raw_secret: str
    provisioning_uri: str


class MfaService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, encryptor: SecretsEncryptor | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self._encryptor = encryptor or get_default_encryptor()

    async def enroll_totp(self, user_id: str, *, account_email: str) -> EnrollmentResult:
        existing = await self.repos.mfa_factors.get_active_for_user(user_id)
        if existing is not None:
            raise ConflictError("user already has an active MFA factor")

        raw_secret = generate_totp_secret()
        factor = MfaFactorModel(
            user_id=user_id, factor_type=MfaFactorType.TOTP.value,
            secret_encrypted=self._encryptor.encrypt(raw_secret), status=MfaFactorStatus.PENDING.value,
        )
        await self.repos.mfa_factors.add(factor)

        uri = provisioning_uri(
            raw_secret, account_name=account_email, issuer=self.settings.totp_issuer,
            digits=self.settings.totp_digits, period=self.settings.totp_period_seconds,
        )
        return EnrollmentResult(factor_id=factor.id, raw_secret=raw_secret, provisioning_uri=uri)

    async def confirm_enrollment(self, factor_id: str, code: str) -> list[str]:
        """Verifies the first code from the authenticator app, activates
        the factor, and returns a freshly generated batch of raw
        recovery codes (shown to the user exactly once)."""
        factor = await self.repos.mfa_factors.get_or_404(factor_id)
        raw_secret = self._encryptor.decrypt(factor.secret_encrypted)
        if not verify_totp(raw_secret, code, period=self.settings.totp_period_seconds, digits=self.settings.totp_digits):
            raise InvalidMfaCodeError("TOTP code is incorrect")

        entity = mfa_factor_to_domain(factor)
        entity.verify()
        apply_mfa_factor_domain_to_model(entity, factor)
        await self.repos.mfa_factors.update(factor)

        return await self.generate_recovery_codes(factor.user_id)

    async def has_active_factor(self, user_id: str) -> bool:
        return await self.repos.mfa_factors.get_active_for_user(user_id) is not None

    async def verify_login_code(self, user_id: str, code: str) -> bool:
        """Tries the user's active TOTP factor first, then falls back to
        a recovery code. Returns True on success (never raises for a bad
        code — callers decide how to respond, e.g. rate-limit)."""
        factor = await self.repos.mfa_factors.get_active_for_user(user_id)
        if factor is not None:
            raw_secret = self._encryptor.decrypt(factor.secret_encrypted)
            if verify_totp(raw_secret, code, period=self.settings.totp_period_seconds, digits=self.settings.totp_digits):
                return True
        return await self.redeem_recovery_code(user_id, code)

    async def generate_recovery_codes(self, user_id: str) -> list[str]:
        """Invalidates any still-unused codes from a prior batch and
        issues a fresh set — rotating recovery codes always fully
        replaces the old batch, never appends to it."""
        for stale in await self.repos.recovery_codes.list_unused_for_user(user_id):
            await self.repos.recovery_codes.delete(stale, hard=True)

        raw_codes: list[str] = []
        for _ in range(self.settings.recovery_code_count):
            raw = generate_raw_token(num_bytes=8)
            raw_codes.append(raw)
            await self.repos.recovery_codes.add(RecoveryCodeModel(user_id=user_id, code_hash=hash_token(raw)))
        return raw_codes

    async def redeem_recovery_code(self, user_id: str, raw_code: str) -> bool:
        code = await self.repos.recovery_codes.get_by_code_hash(hash_token(raw_code))
        if code is None or code.user_id != user_id or code.used_at is not None:
            return False
        code.used_at = utcnow()
        await self.repos.recovery_codes.update(code)
        return True

    async def remaining_recovery_code_count(self, user_id: str) -> int:
        return len(await self.repos.recovery_codes.list_unused_for_user(user_id))

    async def disable_factor(self, factor_id: str) -> MfaFactorModel:
        factor = await self.repos.mfa_factors.get_or_404(factor_id)
        entity = mfa_factor_to_domain(factor)
        entity.disable()
        apply_mfa_factor_domain_to_model(entity, factor)
        return await self.repos.mfa_factors.update(factor)

    async def has_exhausted_recovery_codes(self, user_id: str) -> None:
        if await self.remaining_recovery_code_count(user_id) == 0:
            raise RecoveryCodeExhaustedError(f"user '{user_id}' has no remaining recovery codes")
