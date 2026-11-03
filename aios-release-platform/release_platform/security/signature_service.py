"""Artifact signing: an HMAC signature over an artifact's bytes,
reusing `security.tokens.sign_payload` — the same shared-secret
signing primitive `licensing.license_rules` uses for offline license
validation. Signing an artifact flips its `signed` flag directly (the
one place this platform crosses from the security module into the
artifacts module), since "has this artifact been signed" is
definitionally a security-module fact about an artifacts-module row."""
from __future__ import annotations

from release_platform.core.exceptions import ArtifactNotFoundError, SignatureVerificationFailedError
from release_platform.models.security import ArtifactSignatureModel
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.security.tokens import sign_payload


class ArtifactSignatureService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def sign_artifact(
        self, tenant_id: str, *, artifact_id: str, payload: bytes, secret: str, algorithm: str = "sha256", signed_by: str | None = None
    ) -> ArtifactSignatureModel:
        artifact = await self.repos.artifacts.get(artifact_id)
        if artifact is None or artifact.tenant_id != tenant_id:
            raise ArtifactNotFoundError(f"Artifact '{artifact_id}' not found for tenant '{tenant_id}'")
        signature_value = sign_payload(payload, secret, algorithm=algorithm)
        signature = ArtifactSignatureModel(
            tenant_id=tenant_id, artifact_id=artifact_id, signature=signature_value, algorithm=algorithm, signed_by=signed_by,
        )
        signature = await self.repos.artifact_signatures.add(signature)
        artifact.signed = True
        await self.repos.artifacts.update(artifact)
        return signature

    async def verify_artifact_signature(self, tenant_id: str, *, artifact_id: str, payload: bytes, secret: str) -> ArtifactSignatureModel:
        signatures = await self.repos.artifact_signatures.list_for_artifact(tenant_id, artifact_id)
        if not signatures:
            raise SignatureVerificationFailedError(f"Artifact '{artifact_id}' has no signature on record")
        latest = signatures[-1]
        expected = sign_payload(payload, secret, algorithm=latest.algorithm)
        if expected != latest.signature:
            raise SignatureVerificationFailedError(f"Signature verification failed for artifact '{artifact_id}'")
        return latest

    async def list_for_artifact(self, tenant_id: str, artifact_id: str) -> list[ArtifactSignatureModel]:
        return await self.repos.artifact_signatures.list_for_artifact(tenant_id, artifact_id)
