"""Enterprise version control for prompts: history, diff, rollback,
branching (experimental/stable/production lanes), comparison, change
tracking, and the approval workflow. Business rules (legal transitions,
the production eval-score gate) live in the domain aggregate
(domain/entities.py) — this service's job is loading the right ORM rows,
running them through the domain aggregate, and persisting the result.
"""
from __future__ import annotations

import difflib


from prompt_platform.core.exceptions import SecurityViolationError
from prompt_platform.domain.enums import VersionBranch
from prompt_platform.models.version import PromptHistoryModel, PromptReleaseModel, PromptVersionModel
from prompt_platform.prompt_engine.mappers import (
    apply_version_domain_to_model,
    prompt_to_domain,
    version_to_domain,
)
from prompt_platform.prompt_security.security_service import SecurityService, scan_text
from prompt_platform.repositories.registry import RepositoryRegistry
from prompt_platform.clock import utc_now


class VersioningService:
    def __init__(self, repos: RepositoryRegistry, *, min_production_eval_score: float = 85.0, security: SecurityService | None = None):
        self.repos = repos
        self.min_production_eval_score = min_production_eval_score
        self.security = security or SecurityService()

    async def _load_prompt_aggregate(self, prompt_id: str):
        prompt_model = await self.repos.prompts.get_or_404(prompt_id)
        version_models = await self.repos.versions.list_for_prompt(prompt_id)
        return prompt_model, version_models, prompt_to_domain(prompt_model, version_models)

    async def create_version(
        self, prompt_id: str, *, user_template: str, actor_id: str,
        system_template: str | None = None, developer_template: str | None = None,
        variables_schema: list[dict] | None = None, parameters: dict | None = None,
        parent_version_id: str | None = None,
    ) -> PromptVersionModel:
        # Hard-fail before persisting anything if the draft template text
        # contains what looks like a hardcoded secret (see prompt_security).
        for text in (system_template, developer_template, user_template):
            report = scan_text(text)
            if report.has_secrets:
                raise SecurityViolationError(
                    f"Template contains what looks like hardcoded secret(s): {', '.join(report.secret_matches)}. "
                    "Move secrets to environment config instead of embedding them in template text."
                )

        prompt_model, _, prompt_entity = await self._load_prompt_aggregate(prompt_id)
        new_version_entity = prompt_entity.add_version(
            version_id="__pending__",  # replaced by the DB-generated id below
            user_template=user_template, system_template=system_template, developer_template=developer_template,
            variables_schema=variables_schema, parameters=parameters, parent_version_id=parent_version_id,
        )
        version_model = PromptVersionModel(
            prompt_id=prompt_id, version_number=new_version_entity.version_number,
            user_template=user_template, system_template=system_template, developer_template=developer_template,
            variables_schema=variables_schema or [], parameters=parameters or {},
            parent_version_id=new_version_entity.parent_version_id, created_by=actor_id,
        )
        version_model = await self.repos.versions.add(version_model)

        prompt_model.latest_version_number = prompt_entity.latest_version_number
        await self.repos.prompts.update(prompt_model)
        await self._record_history(prompt_id, version_model.id, actor_id, "version_created", before=None, after={"version_number": version_model.version_number})
        return version_model

    async def submit_for_review(self, version_id: str, actor_id: str) -> PromptVersionModel:
        model = await self.repos.versions.get_or_404(version_id)
        entity = version_to_domain(model)
        entity.submit_for_review(actor_id)
        apply_version_domain_to_model(entity, model)
        updated = await self.repos.versions.update(model)
        await self._record_history(model.prompt_id, version_id, actor_id, "version_submitted_for_review", before=None, after=None)
        return updated

    async def approve(self, version_id: str, actor_id: str) -> PromptVersionModel:
        model = await self.repos.versions.get_or_404(version_id)
        entity = version_to_domain(model)
        entity.approve(actor_id)
        apply_version_domain_to_model(entity, model)
        updated = await self.repos.versions.update(model)
        await self._record_history(model.prompt_id, version_id, actor_id, "version_approved", before=None, after=None)
        return updated

    async def reject(self, version_id: str, actor_id: str, reason: str) -> PromptVersionModel:
        model = await self.repos.versions.get_or_404(version_id)
        entity = version_to_domain(model)
        entity.reject(actor_id, reason)
        apply_version_domain_to_model(entity, model)
        updated = await self.repos.versions.update(model)
        await self._record_history(model.prompt_id, version_id, actor_id, "version_rejected", before=None, after={"reason": reason})
        return updated

    async def record_eval_score(self, version_id: str, score: float) -> PromptVersionModel:
        model = await self.repos.versions.get_or_404(version_id)
        model.eval_score = score
        return await self.repos.versions.update(model)

    async def promote(
        self, prompt_id: str, version_id: str, target_branch: VersionBranch, actor_id: str, *, release_notes: str | None = None
    ) -> PromptVersionModel:
        prompt_model, version_models, prompt_entity = await self._load_prompt_aggregate(prompt_id)
        target_entity = prompt_entity.get_version(version_id)
        previous_production_id = prompt_entity.production_version_id

        prompt_entity.promote_version(target_entity, target_branch, min_production_eval_score=self.min_production_eval_score)

        target_model = next(v for v in version_models if v.id == version_id)
        target_model.branch = target_entity.branch.value
        target_model.release_notes = release_notes or target_model.release_notes
        await self.repos.versions.update(target_model)

        if target_branch == VersionBranch.PRODUCTION and previous_production_id and previous_production_id != version_id:
            previous_model = next((v for v in version_models if v.id == previous_production_id), None)
            if previous_model is not None:
                previous_model.branch = VersionBranch.STABLE.value
                await self.repos.versions.update(previous_model)

        prompt_model.production_version_id = prompt_entity.production_version_id
        prompt_model.stable_version_id = prompt_entity.stable_version_id
        await self.repos.prompts.update(prompt_model)

        await self.repos.releases.add(
            PromptReleaseModel(
                prompt_id=prompt_id, version_id=version_id, environment=target_branch.value,
                release_notes=release_notes, released_by=actor_id, released_at=utc_now(),
            )
        )
        await self._record_history(prompt_id, version_id, actor_id, f"version_promoted_to_{target_branch.value}", before=None, after=None)
        return target_model

    async def rollback(self, prompt_id: str, target_version_id: str, actor_id: str, *, reason: str | None = None) -> PromptVersionModel:
        """Re-promotes a previously-approved version back onto the
        PRODUCTION branch — its stored eval_score (from when it was first
        promoted) is reused, so a version that already cleared the quality
        gate once doesn't need to clear it again to be restored."""
        return await self.promote(
            prompt_id, target_version_id, VersionBranch.PRODUCTION, actor_id,
            release_notes=f"Rollback: {reason}" if reason else "Rollback",
        )

    # -- diff / comparison ---------------------------------------------------

    def diff_text(self, a: str | None, b: str | None) -> list[str]:
        return list(difflib.unified_diff((a or "").splitlines(), (b or "").splitlines(), lineterm="", fromfile="version_a", tofile="version_b"))

    async def diff_versions(self, version_id_a: str, version_id_b: str) -> dict:
        a = await self.repos.versions.get_or_404(version_id_a)
        b = await self.repos.versions.get_or_404(version_id_b)
        return {
            "system_template_diff": self.diff_text(a.system_template, b.system_template),
            "developer_template_diff": self.diff_text(a.developer_template, b.developer_template),
            "user_template_diff": self.diff_text(a.user_template, b.user_template),
            "parameter_changes": self._dict_diff(a.parameters or {}, b.parameters or {}),
            "variable_changes": self._list_diff(
                [v["name"] for v in (a.variables_schema or [])], [v["name"] for v in (b.variables_schema or [])]
            ),
            "status_a": a.status, "status_b": b.status,
            "eval_score_a": a.eval_score, "eval_score_b": b.eval_score,
        }

    def _dict_diff(self, a: dict, b: dict) -> dict:
        added = {k: b[k] for k in b.keys() - a.keys()}
        removed = {k: a[k] for k in a.keys() - b.keys()}
        changed = {k: {"from": a[k], "to": b[k]} for k in a.keys() & b.keys() if a[k] != b[k]}
        return {"added": added, "removed": removed, "changed": changed}

    def _list_diff(self, a: list[str], b: list[str]) -> dict:
        return {"added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b))}

    # -- history / listing -----------------------------------------------------

    async def history(self, prompt_id: str, *, limit: int = 100) -> list[PromptHistoryModel]:
        return await self.repos.history.list_for_prompt(prompt_id, limit=limit)

    async def list_versions(self, prompt_id: str) -> list[PromptVersionModel]:
        return await self.repos.versions.list_for_prompt(prompt_id)

    async def _record_history(self, prompt_id: str, version_id: str | None, actor_id: str, action: str, *, before, after) -> None:
        await self.repos.history.add(
            PromptHistoryModel(
                prompt_id=prompt_id, version_id=version_id, actor_id=actor_id, action=action,
                before=before, after=after, created_at=utc_now(),
            )
        )
