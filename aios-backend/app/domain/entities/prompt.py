"""Prompt aggregate — the richest example of business rules living in the
domain layer rather than scattered across routers/services.

A `Prompt` owns a list of `PromptVersion`s. Promotion rules (draft -> staged
-> production) are enforced here so no matter which service/route calls
into this aggregate, the same invariants hold: you cannot promote to
production below the evaluation score threshold, and promoting a version to
production automatically demotes whichever version currently holds it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.exceptions import UnprocessableStateError, ValidationError
from app.domain.value_objects.enums import PromptStatus

MIN_PRODUCTION_EVAL_SCORE = 90.0

_ALLOWED_TRANSITIONS: dict[PromptStatus, set[PromptStatus]] = {
    PromptStatus.DRAFT: {PromptStatus.STAGED, PromptStatus.ARCHIVED},
    PromptStatus.STAGED: {PromptStatus.PRODUCTION, PromptStatus.DRAFT, PromptStatus.ARCHIVED},
    PromptStatus.PRODUCTION: {PromptStatus.ARCHIVED},
    PromptStatus.ARCHIVED: set(),
}


@dataclass
class PromptVersion:
    id: str
    prompt_id: str
    version: int
    content: str
    status: PromptStatus
    author_id: str
    created_at: datetime
    eval_score: float | None = None

    def can_transition_to(self, target: PromptStatus) -> bool:
        return target in _ALLOWED_TRANSITIONS.get(self.status, set())

    def promote(self, target: PromptStatus, *, enforce_eval_gate: bool = True) -> None:
        if not self.can_transition_to(target):
            raise UnprocessableStateError(
                f"Cannot transition prompt version from {self.status.value} to {target.value}",
                current_status=self.status.value,
                target_status=target.value,
            )
        if target == PromptStatus.PRODUCTION and enforce_eval_gate:
            if self.eval_score is None or self.eval_score < MIN_PRODUCTION_EVAL_SCORE:
                raise UnprocessableStateError(
                    f"Promotion to production requires an evaluation score >= {MIN_PRODUCTION_EVAL_SCORE}",
                    eval_score=self.eval_score,
                )
        self.status = target


@dataclass
class Prompt:
    id: str
    workspace_id: str
    name: str
    description: str
    target_model: str
    tags: list[str] = field(default_factory=list)
    versions: list[PromptVersion] = field(default_factory=list)

    @property
    def latest_version(self) -> PromptVersion | None:
        return max(self.versions, key=lambda v: v.version, default=None)

    @property
    def production_version(self) -> PromptVersion | None:
        return next((v for v in self.versions if v.status == PromptStatus.PRODUCTION), None)

    def next_version_number(self) -> int:
        return (self.latest_version.version if self.latest_version else 0) + 1

    def add_version(self, content: str, author_id: str, created_at: datetime) -> PromptVersion:
        if not content.strip():
            raise ValidationError("Prompt content must not be empty")
        version = PromptVersion(
            id="",  # assigned by repository on persist
            prompt_id=self.id,
            version=self.next_version_number(),
            content=content,
            status=PromptStatus.DRAFT,
            author_id=author_id,
            created_at=created_at,
        )
        self.versions.append(version)
        return version

    def promote_version(self, version_number: int, target: PromptStatus) -> PromptVersion:
        version = next((v for v in self.versions if v.version == version_number), None)
        if version is None:
            from app.domain.exceptions import NotFoundError

            raise NotFoundError(f"Prompt version {version_number} not found")

        # Promoting a new production version demotes the previous one, so
        # "exactly one production version at a time" is an invariant the
        # aggregate itself enforces rather than something callers must
        # remember to do.
        if target == PromptStatus.PRODUCTION:
            current_prod = self.production_version
            version.promote(target)
            if current_prod and current_prod.version != version.version:
                current_prod.status = PromptStatus.ARCHIVED
        else:
            version.promote(target)
        return version
