import pytest

from release_platform.artifacts.artifact_service import ArtifactService
from release_platform.core.exceptions import ArtifactNotFoundError, SignatureVerificationFailedError
from release_platform.security.signature_service import ArtifactSignatureService

pytestmark = pytest.mark.asyncio

TENANT = "t-security"


async def test_sign_artifact_requires_existing_artifact(repos):
    svc = ArtifactSignatureService(repos)
    with pytest.raises(ArtifactNotFoundError):
        await svc.sign_artifact(TENANT, artifact_id="nonexistent", payload=b"data", secret="shh")


async def test_sign_artifact_flips_signed_flag(repos):
    artifact_svc = ArtifactService(repos)
    sig_svc = ArtifactSignatureService(repos)
    artifact = await artifact_svc.register_artifact(TENANT, release_id="r1", artifact_type="docker_image", name="backend", version="1.0.0")
    assert artifact.signed is False

    await sig_svc.sign_artifact(TENANT, artifact_id=artifact.id, payload=b"image-bytes", secret="shh")
    refreshed = await artifact_svc.get_or_404(TENANT, artifact.id)
    assert refreshed.signed is True


async def test_verify_artifact_signature_succeeds_with_correct_payload(repos):
    artifact_svc = ArtifactService(repos)
    sig_svc = ArtifactSignatureService(repos)
    artifact = await artifact_svc.register_artifact(TENANT, release_id="r2", artifact_type="cli_package", name="aios-cli", version="1.0.0")
    await sig_svc.sign_artifact(TENANT, artifact_id=artifact.id, payload=b"cli-bytes", secret="shh")

    await sig_svc.verify_artifact_signature(TENANT, artifact_id=artifact.id, payload=b"cli-bytes", secret="shh")


async def test_verify_artifact_signature_fails_with_no_signature(repos):
    artifact_svc = ArtifactService(repos)
    sig_svc = ArtifactSignatureService(repos)
    artifact = await artifact_svc.register_artifact(TENANT, release_id="r3", artifact_type="sdk_package", name="aios-sdk", version="1.0.0")
    with pytest.raises(SignatureVerificationFailedError):
        await sig_svc.verify_artifact_signature(TENANT, artifact_id=artifact.id, payload=b"sdk-bytes", secret="shh")


async def test_verify_artifact_signature_fails_with_tampered_payload(repos):
    artifact_svc = ArtifactService(repos)
    sig_svc = ArtifactSignatureService(repos)
    artifact = await artifact_svc.register_artifact(TENANT, release_id="r4", artifact_type="docker_image", name="backend", version="1.1.0")
    await sig_svc.sign_artifact(TENANT, artifact_id=artifact.id, payload=b"original-bytes", secret="shh")
    with pytest.raises(SignatureVerificationFailedError):
        await sig_svc.verify_artifact_signature(TENANT, artifact_id=artifact.id, payload=b"tampered-bytes", secret="shh")
