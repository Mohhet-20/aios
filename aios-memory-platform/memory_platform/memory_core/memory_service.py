"""MemoryService — the generic lifecycle engine every one of the 16
memory types runs through: creation, retrieval (with access tracking),
update/versioning, summarization/compression, importance scoring/decay,
conflict resolution (supersession), archiving/restoring, expiration,
retention enforcement, deletion, and audit history. Parameterized by
`MemoryType` + the data-driven `MemoryTypePolicyModel` row rather than
one class per type — the same "extensibility via data" lesson the Agent
Platform's `AgentTypeModel` established.

The handful of memory types with a genuinely distinct interaction shape
(conversation turns, timestamped episodes, TTL-bound working focus) get
a thin service on top of this one (see `conversation_memory/`,
`episodic_memory/`, `memory_core/working_memory_service.py`) rather than
a special case inside it.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest

from memory_platform.core.exceptions import ValidationError
from memory_platform.database.base import new_uuid
from memory_platform.domain.enums import MemoryStatus, MemoryType
from memory_platform.memory_core.mappers import apply_to_model, to_domain
from memory_platform.models.memory_entry import MemoryEntryModel
from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


class MemoryService:
    def __init__(self, repos: RepositoryRegistry, *, ai_core: AICoreContext | None = None):
        self.repos = repos
        self.ai_core = ai_core

    # -- policy lookup ---------------------------------------------------------

    async def _policy_defaults(self, memory_type: str) -> dict:
        policy = await self.repos.memory_type_policies.get_by_key(memory_type)
        if policy is None:
            return {"default_importance": 0.5, "default_retention_days": None, "decay_rate": 0.02,
                    "summarize_after_tokens": None, "max_entries_per_scope": None}
        return {
            "default_importance": policy.default_importance,
            "default_retention_days": policy.default_retention_days,
            "decay_rate": policy.decay_rate,
            "summarize_after_tokens": policy.summarize_after_tokens,
            "max_entries_per_scope": policy.max_entries_per_scope,
        }

    # -- audit -------------------------------------------------------------------

    async def _audit(self, actor_id: str, action: str, resource_id: str, *, before: dict | None = None, after: dict | None = None) -> None:
        from memory_platform.models.governance import AuditLogEntryModel

        await self.repos.audit_log.add(AuditLogEntryModel(
            actor_id=actor_id, action=action, resource_type="memory_entry", resource_id=resource_id, before=before, after=after,
        ))

    # -- creation ------------------------------------------------------------------

    async def create(
        self, *, workspace_id: str, memory_type: MemoryType | str, scope_type: str, scope_id: str, content: str,
        actor_id: str = "system", title: str | None = None, structured_content: dict | None = None,
        importance_score: float | None = None, confidence: float | None = None, source: str | None = None,
        source_type: str | None = None, tags: list | None = None, sensitivity_level: str = "internal",
        conversation_id: str | None = None, turn_index: int | None = None, occurred_at: datetime | None = None,
        retention_days_override: int | None = None,
    ) -> MemoryEntryModel:
        mtype = memory_type.value if isinstance(memory_type, MemoryType) else memory_type
        if not content or not content.strip():
            raise ValidationError("memory content must not be empty")

        defaults = await self._policy_defaults(mtype)
        retention_days = retention_days_override if retention_days_override is not None else defaults["default_retention_days"]
        expires_at = (_now() + timedelta(days=retention_days)) if retention_days is not None else None

        # max_entries_per_scope enforcement (e.g. WORKING memory keeps exactly one "current focus")
        max_entries = defaults.get("max_entries_per_scope")
        if max_entries is not None:
            existing = await self.repos.memory_entries.list_for_scope(workspace_id, scope_type, scope_id, memory_type=mtype, status=MemoryStatus.ACTIVE.value)
            if len(existing) >= max_entries:
                for stale in existing[max_entries - 1:]:
                    stale_entity = to_domain(stale)
                    stale_entity.archive()
                    apply_to_model(stale_entity, stale)

        model = MemoryEntryModel(
            id=new_uuid(), workspace_id=workspace_id, memory_type=mtype, scope_type=scope_type, scope_id=scope_id,
            title=title, content=content, structured_content=structured_content,
            importance_score=importance_score if importance_score is not None else defaults["default_importance"],
            confidence=confidence, source=source, source_type=source_type, tags=tags or [],
            status=MemoryStatus.ACTIVE.value, sensitivity_level=sensitivity_level,
            conversation_id=conversation_id, turn_index=turn_index, occurred_at=occurred_at, expires_at=expires_at,
        )
        created = await self.repos.memory_entries.add(model)
        await self._audit(actor_id, "memory.create", created.id, after={"memory_type": mtype, "scope_type": scope_type, "scope_id": scope_id})
        return created

    # -- retrieval -------------------------------------------------------------------

    async def get(self, memory_id: str, *, record_access: bool = True, actor_id: str = "system") -> MemoryEntryModel:
        model = await self.repos.memory_entries.get_or_404(memory_id)
        if record_access and model.status == MemoryStatus.ACTIVE.value:
            entity = to_domain(model)
            entity.record_access()
            apply_to_model(entity, model)
            await self.repos.memory_entries.update(model)
        return model

    async def list_for_scope(self, workspace_id: str, scope_type: str, scope_id: str, *, memory_type: str | None = None, status: str | None = None, limit: int = 200) -> list[MemoryEntryModel]:
        return await self.repos.memory_entries.list_for_scope(workspace_id, scope_type, scope_id, memory_type=memory_type, status=status, limit=limit)

    async def search_keyword(self, workspace_id: str, query: str, *, memory_type: str | None = None, limit: int = 50) -> list[MemoryEntryModel]:
        return await self.repos.memory_entries.search_keyword(workspace_id, query, memory_type=memory_type, limit=limit)

    # -- update / versioning -------------------------------------------------------

    async def update_content(self, memory_id: str, content: str, *, structured_content: dict | None = None, actor_id: str = "system") -> MemoryEntryModel:
        model = await self.repos.memory_entries.get_or_404(memory_id)
        before = {"content": model.content, "version": model.version}
        entity = to_domain(model)
        entity.update_content(content, structured_content=structured_content)
        apply_to_model(entity, model)
        await self.repos.memory_entries.update(model)
        await self._audit(actor_id, "memory.update", model.id, before=before, after={"content": model.content, "version": model.version})
        return model

    # -- summarization / compression ------------------------------------------------

    async def summarize(self, memory_id: str, summary_text: str, *, actor_id: str = "system") -> MemoryEntryModel:
        model = await self.repos.memory_entries.get_or_404(memory_id)
        entity = to_domain(model)
        entity.summarize(summary_text)
        apply_to_model(entity, model)
        await self.repos.memory_entries.update(model)
        await self._audit(actor_id, "memory.summarize", model.id, after={"summary": summary_text})
        return model

    async def summarize_with_llm(self, memory_id: str, *, actor_id: str = "system", max_summary_tokens: int = 200) -> MemoryEntryModel:
        """Real LLM-backed compression — used when content exceeds the
        type's `summarize_after_tokens` policy threshold."""
        if self.ai_core is None:
            raise ValidationError("summarize_with_llm requires an AICoreContext")
        model = await self.repos.memory_entries.get_or_404(memory_id)
        messages = [
            ChatMessage(role=Role.SYSTEM, content=f"Summarize the following memory content in at most {max_summary_tokens} tokens, preserving the key facts."),
            ChatMessage(role=Role.USER, content=model.content),
        ]
        response = await self.ai_core.execution_engine.generate(GenerationRequest(messages=messages, temperature=0.2))
        return await self.summarize(memory_id, response.content.strip(), actor_id=actor_id)

    async def maybe_compress(self, memory_id: str, *, actor_id: str = "system") -> MemoryEntryModel:
        """Checks the owning type's policy and triggers LLM summarization
        only if content length crosses `summarize_after_tokens`."""
        from ai_core.tokenizer.counter import count_tokens

        model = await self.repos.memory_entries.get_or_404(memory_id)
        defaults = await self._policy_defaults(model.memory_type)
        threshold = defaults.get("summarize_after_tokens")
        if threshold is None or model.summary is not None:
            return model
        if count_tokens(model.content) < threshold:
            return model
        return await self.summarize_with_llm(memory_id, actor_id=actor_id)

    # -- lifecycle -----------------------------------------------------------------

    async def archive(self, memory_id: str, *, actor_id: str = "system") -> MemoryEntryModel:
        return await self._transition(memory_id, "archive", actor_id)

    async def restore(self, memory_id: str, *, actor_id: str = "system") -> MemoryEntryModel:
        return await self._transition(memory_id, "restore", actor_id)

    async def expire(self, memory_id: str, *, actor_id: str = "system") -> MemoryEntryModel:
        return await self._transition(memory_id, "expire", actor_id)

    async def delete(self, memory_id: str, *, actor_id: str = "system", hard: bool = False) -> None:
        model = await self.repos.memory_entries.get_or_404(memory_id)
        entity = to_domain(model)
        entity.delete()
        apply_to_model(entity, model)
        await self.repos.memory_entries.update(model)
        await self._audit(actor_id, "memory.delete", model.id)
        if hard:
            await self.repos.memory_entries.delete(model, hard=True)

    async def _transition(self, memory_id: str, action: str, actor_id: str) -> MemoryEntryModel:
        model = await self.repos.memory_entries.get_or_404(memory_id)
        before = {"status": model.status}
        entity = to_domain(model)
        getattr(entity, action)()
        apply_to_model(entity, model)
        await self.repos.memory_entries.update(model)
        await self._audit(actor_id, f"memory.{action}", model.id, before=before, after={"status": model.status})
        return model

    # -- conflict resolution ---------------------------------------------------------

    async def supersede(self, old_memory_id: str, *, content: str, actor_id: str = "system", structured_content: dict | None = None) -> MemoryEntryModel:
        """Conflict resolution: a newer fact replaces an old one. The old
        entry transitions to SUPERSEDED and points at the new one rather
        than being overwritten or destroyed, keeping it inspectable."""
        old = await self.repos.memory_entries.get_or_404(old_memory_id)
        new_model = await self.create(
            workspace_id=old.workspace_id, memory_type=old.memory_type, scope_type=old.scope_type, scope_id=old.scope_id,
            content=content, actor_id=actor_id, title=old.title, structured_content=structured_content,
            importance_score=old.importance_score, source=old.source, source_type=old.source_type,
            tags=list(old.tags or []), sensitivity_level=old.sensitivity_level,
        )
        entity = to_domain(old)
        entity.supersede(new_model.id)
        apply_to_model(entity, old)
        await self.repos.memory_entries.update(old)
        await self._audit(actor_id, "memory.supersede", old.id, before={"status": "active"}, after={"status": "superseded", "superseded_by_id": new_model.id})
        return new_model

    # -- importance / decay -----------------------------------------------------------

    async def decayed_importance(self, memory_id: str, *, as_of: datetime | None = None) -> float:
        model = await self.repos.memory_entries.get_or_404(memory_id)
        entity = to_domain(model)
        defaults = await self._policy_defaults(model.memory_type)
        return entity.decayed_importance(defaults["decay_rate"], as_of=as_of)

    # -- retention enforcement --------------------------------------------------------

    async def apply_retention_policies(self, workspace_id: str, *, actor_id: str = "system", as_of: datetime | None = None) -> dict:
        """Sweeps ACTIVE entries whose `expires_at` has passed and expires
        them (governance's scheduled retention job, or the API, calls
        this). Returns a summary of what happened for observability."""
        as_of = as_of or _now()
        candidates = await self.repos.memory_entries.list_expired_candidates(workspace_id, as_of=as_of)
        expired_ids: list[str] = []
        for model in candidates:
            entity = to_domain(model)
            entity.expire()
            apply_to_model(entity, model)
            await self.repos.memory_entries.update(model)
            await self._audit(actor_id, "memory.expire", model.id, before={"status": "active"}, after={"status": "expired"})
            expired_ids.append(model.id)
        return {"workspace_id": workspace_id, "expired_count": len(expired_ids), "expired_ids": expired_ids, "as_of": as_of.isoformat()}

    # -- audit history -----------------------------------------------------------------

    async def audit_history(self, memory_id: str) -> list:
        return await self.repos.audit_log.list_for_resource("memory_entry", memory_id)
