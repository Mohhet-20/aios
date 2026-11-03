"""CredentialModel: the vault. `encrypted_payload` is always Fernet-
ciphertext (never plaintext at rest) — see `credentials/vault_service.py`
for the encrypt/decrypt boundary, which mirrors the Workflow Engine's
`is_secret` variable encryption. `ToolCredentialBindingModel` is the
"which credential does this tool use in this workspace" link, kept
separate from the credential itself so one credential (e.g. a shared
GitHub service account) can back multiple tools."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin
from tool_platform.domain.enums import CredentialStatus


class CredentialModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "tp_credentials"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_workspaces.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=CredentialStatus.ACTIVE.value, nullable=False, index=True)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False, doc="Fernet ciphertext of the actual secret material (key/token/refresh token/...)")
    scopes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rotated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    credential_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Non-secret context: e.g. OAuth2 token endpoint, issuer, client_id (never the secret itself)")


class ToolCredentialBindingModel(Base, IdMixin):
    __tablename__ = "tp_tool_credential_bindings"

    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tools.id"), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    credential_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_credentials.id"), nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(default=True, nullable=False)
