"""Pure-Python domain aggregates for the flagship Prompt/PromptVersion
concept — no ORM/framework imports, so business rules (approval workflow,
branch promotion, eval-score gating) are testable in isolation and can't
be bypassed by a service that forgets to call the right repository
method. Mirrors the AIOS backend's Prompt/PromptVersion aggregate
(the core backend) but is the flagship, most-detailed aggregate in *this*
platform rather than one of many.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from prompt_platform.core.exceptions import EvalGateNotMetError, InvalidTransitionError
from prompt_platform.domain.enums import PromptStatus, VersionBranch, VersionStatus
from prompt_platform.clock import utc_now

_STATUS_TRANSITIONS: dict[VersionStatus, set[VersionStatus]] = {
    VersionStatus.DRAFT: {VersionStatus.IN_REVIEW, VersionStatus.ARCHIVED},
    VersionStatus.IN_REVIEW: {VersionStatus.APPROVED, VersionStatus.REJECTED, VersionStatus.DRAFT},
    VersionStatus.APPROVED: {VersionStatus.DEPRECATED, VersionStatus.ARCHIVED},
    VersionStatus.REJECTED: {VersionStatus.DRAFT, VersionStatus.ARCHIVED},
    VersionStatus.DEPRECATED: {VersionStatus.ARCHIVED},
    VersionStatus.ARCHIVED: set(),
}


def _now() -> datetime:
    return utc_now()


@dataclass
class PromptVersion:
    id: str
    prompt_id: str
    version_number: int
    user_template: str
    system_template: str | None = None
    developer_template: str | None = None
    variables_schema: list[dict] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)
    status: VersionStatus = VersionStatus.DRAFT
    branch: VersionBranch = VersionBranch.EXPERIMENTAL
    release_notes: str | None = None
    eval_score: float | None = None
    parent_version_id: str | None = None
    submitted_for_review_by: str | None = None
    submitted_for_review_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None

    def _transition(self, target: VersionStatus) -> None:
        allowed = _STATUS_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"cannot move version {self.id} from {self.status.value} to {target.value}")
        self.status = target

    def submit_for_review(self, actor_id: str) -> None:
        self._transition(VersionStatus.IN_REVIEW)
        self.submitted_for_review_by = actor_id
        self.submitted_for_review_at = _now()

    def approve(self, actor_id: str) -> None:
        self._transition(VersionStatus.APPROVED)
        self.approved_by = actor_id
        self.approved_at = _now()
        self.rejection_reason = None

    def reject(self, actor_id: str, reason: str) -> None:
        self._transition(VersionStatus.REJECTED)
        self.approved_by = actor_id
        self.approved_at = _now()
        self.rejection_reason = reason

    def resubmit(self) -> None:
        self._transition(VersionStatus.DRAFT)

    def deprecate(self) -> None:
        self._transition(VersionStatus.DEPRECATED)

    def archive(self) -> None:
        self._transition(VersionStatus.ARCHIVED)

    def record_eval_score(self, score: float) -> None:
        self.eval_score = score

    def promote(self, target_branch: VersionBranch, *, min_production_eval_score: float) -> None:
        """Moves this version onto a deployment lane. Requires the
        approval workflow to have completed first (status == APPROVED) —
        branch promotion is not a substitute for review. Promoting onto
        the PRODUCTION branch additionally requires a minimum evaluation
        score, mirroring the AIOS backend's eval-gate pattern."""
        if self.status != VersionStatus.APPROVED:
            raise InvalidTransitionError(
                f"version {self.id} must be APPROVED before promotion to {target_branch.value} (currently {self.status.value})"
            )
        if target_branch == VersionBranch.PRODUCTION:
            if self.eval_score is None or self.eval_score < min_production_eval_score:
                raise EvalGateNotMetError(
                    f"version {self.id} does not meet the production eval-score gate "
                    f"({self.eval_score!r} < {min_production_eval_score})",
                    required=min_production_eval_score, actual=self.eval_score,
                )
        self.branch = target_branch

    def variable_names(self) -> set[str]:
        return {v["name"] for v in self.variables_schema}

    def required_variable_names(self) -> set[str]:
        return {v["name"] for v in self.variables_schema if v.get("required", True)}


@dataclass
class Prompt:
    id: str
    project_id: str
    workspace_id: str
    name: str
    slug: str
    owner_id: str
    status: PromptStatus = PromptStatus.DRAFT
    latest_version_number: int = 0
    production_version_id: str | None = None
    stable_version_id: str | None = None
    versions: list[PromptVersion] = field(default_factory=list)

    def add_version(
        self,
        *,
        version_id: str,
        user_template: str,
        system_template: str | None = None,
        developer_template: str | None = None,
        variables_schema: list[dict] | None = None,
        parameters: dict | None = None,
        parent_version_id: str | None = None,
    ) -> PromptVersion:
        self.latest_version_number += 1
        version = PromptVersion(
            id=version_id,
            prompt_id=self.id,
            version_number=self.latest_version_number,
            user_template=user_template,
            system_template=system_template,
            developer_template=developer_template,
            variables_schema=variables_schema or [],
            parameters=parameters or {},
            parent_version_id=parent_version_id or (self.versions[-1].id if self.versions else None),
        )
        self.versions.append(version)
        return version

    def get_version(self, version_id: str) -> PromptVersion:
        for v in self.versions:
            if v.id == version_id:
                return v
        raise InvalidTransitionError(f"prompt {self.id} has no version {version_id}")

    def promote_version(self, version: PromptVersion, target_branch: VersionBranch, *, min_production_eval_score: float) -> None:
        """Promotes `version` onto `target_branch`. Promoting to PRODUCTION
        demotes whatever version currently holds that branch down to
        STABLE (never silently orphaned — it's still deployed, just no
        longer the head)."""
        version.promote(target_branch, min_production_eval_score=min_production_eval_score)

        if target_branch == VersionBranch.PRODUCTION:
            if self.production_version_id and self.production_version_id != version.id:
                try:
                    previous = self.get_version(self.production_version_id)
                    previous.branch = VersionBranch.STABLE
                    self.stable_version_id = previous.id
                except InvalidTransitionError:
                    pass  # previous production version not loaded in this aggregate instance — service layer handles cross-aggregate demotion
            self.production_version_id = version.id
        elif target_branch == VersionBranch.STABLE:
            self.stable_version_id = version.id

    def activate(self) -> None:
        self.status = PromptStatus.ACTIVE

    def deprecate(self) -> None:
        self.status = PromptStatus.DEPRECATED

    def archive(self) -> None:
        self.status = PromptStatus.ARCHIVED
