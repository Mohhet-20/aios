"""Prompt versioning at the AI Core template layer. This is deliberately
lighter-weight than the AIOS backend's PromptService (the core backend): that
service owns production-promotion business rules, eval-score gating, and
durable Postgres storage for a *product feature* called "Prompt Studio."
This registry just gives any AI Core caller (including that service, or a
standalone script) a versioned in-memory store of template text — render-
only, no promotion workflow. The backend's PromptService is expected to be
the thing that calls into `PromptExecutor` with a template it fetched from
its own store; this registry exists for callers that don't need a full
service (tests, scripts, simple agents).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.enums import Role
from ai_core.utils.exceptions import PromptValidationError


@dataclass
class PromptVersionRecord:
    name: str
    version: int
    template: PromptTemplate
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PromptRegistry:
    def __init__(self) -> None:
        self._versions: dict[str, list[PromptVersionRecord]] = {}

    def register(self, name: str, role: Role, template_text: str) -> PromptVersionRecord:
        existing = self._versions.setdefault(name, [])
        next_version = (existing[-1].version + 1) if existing else 1
        template = PromptTemplate(name=name, role=role, template=template_text, version=next_version)
        record = PromptVersionRecord(name=name, version=next_version, template=template)
        existing.append(record)
        return record

    def get_latest(self, name: str) -> PromptVersionRecord:
        versions = self._versions.get(name)
        if not versions:
            raise PromptValidationError(f"no versions registered for prompt '{name}'")
        return versions[-1]

    def get_version(self, name: str, version: int) -> PromptVersionRecord:
        versions = self._versions.get(name, [])
        for v in versions:
            if v.version == version:
                return v
        raise PromptValidationError(f"prompt '{name}' has no version {version}")

    def list_versions(self, name: str) -> list[PromptVersionRecord]:
        return list(self._versions.get(name, []))
