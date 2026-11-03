"""The 16 memory types' default lifecycle policies — data, not code, so
adding a 17th type or tuning an existing one's retention/decay is a row
change, not a new Python class. Mirrors the Agent Platform's
`seed_builtin_agent_types` pattern exactly.
"""
from __future__ import annotations

from memory_platform.domain.enums import MemoryType
from memory_platform.models.memory_type_policy import MemoryTypePolicyModel
from memory_platform.repositories.registry import RepositoryRegistry

BUILTIN_MEMORY_TYPE_POLICIES: list[dict] = [
    dict(key=MemoryType.WORKING.value, name="Working Memory", description="The agent's current focus within an active session — TTL-bound, not durably retained.",
         default_retention_days=None, default_importance=0.3, decay_rate=0.5, is_persistent=False, summarize_after_tokens=None, max_entries_per_scope=1),
    dict(key=MemoryType.CONVERSATION.value, name="Conversation Memory", description="Ordered turns of a single conversation.",
         default_retention_days=90, default_importance=0.4, decay_rate=0.05, is_persistent=True, summarize_after_tokens=4000, max_entries_per_scope=None),
    dict(key=MemoryType.SESSION.value, name="Session Memory", description="State scoped to one user/agent session.",
         default_retention_days=30, default_importance=0.3, decay_rate=0.1, is_persistent=False, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.SHORT_TERM.value, name="Short-Term Memory", description="Recently learned facts not yet consolidated.",
         default_retention_days=7, default_importance=0.4, decay_rate=0.2, is_persistent=False, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.LONG_TERM.value, name="Long-Term Memory", description="Consolidated, durable recall.",
         default_retention_days=None, default_importance=0.7, decay_rate=0.01, is_persistent=True, summarize_after_tokens=8000, max_entries_per_scope=None),
    dict(key=MemoryType.SEMANTIC.value, name="Semantic Memory", description="Facts and general knowledge, decoupled from any one event.",
         default_retention_days=None, default_importance=0.7, decay_rate=0.005, is_persistent=True, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.EPISODIC.value, name="Episodic Memory", description="Timestamped events — what happened, and when.",
         default_retention_days=365, default_importance=0.5, decay_rate=0.02, is_persistent=True, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.PROCEDURAL.value, name="Procedural Memory", description="How-to knowledge — steps/procedures an agent has learned.",
         default_retention_days=None, default_importance=0.75, decay_rate=0.005, is_persistent=True, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.SHARED_TEAM.value, name="Shared Team Memory", description="Knowledge shared across a team's agents and members.",
         default_retention_days=180, default_importance=0.6, decay_rate=0.02, is_persistent=True, summarize_after_tokens=6000, max_entries_per_scope=None),
    dict(key=MemoryType.ORGANIZATIONAL.value, name="Organizational Memory", description="Org-wide durable knowledge.",
         default_retention_days=None, default_importance=0.8, decay_rate=0.005, is_persistent=True, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.PROJECT.value, name="Project Memory", description="Knowledge scoped to a single project's lifetime.",
         default_retention_days=365, default_importance=0.6, decay_rate=0.02, is_persistent=True, summarize_after_tokens=6000, max_entries_per_scope=None),
    dict(key=MemoryType.USER.value, name="User Memory", description="Durable preferences and facts about a specific user.",
         default_retention_days=730, default_importance=0.6, decay_rate=0.01, is_persistent=True, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.AGENT.value, name="Agent Memory", description="An individual agent's own accumulated recall.",
         default_retention_days=180, default_importance=0.5, decay_rate=0.03, is_persistent=True, summarize_after_tokens=4000, max_entries_per_scope=None),
    dict(key=MemoryType.WORKFLOW.value, name="Workflow Memory", description="State scoped to one workflow definition across its runs.",
         default_retention_days=90, default_importance=0.5, decay_rate=0.03, is_persistent=True, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.EXECUTION.value, name="Execution Memory", description="State scoped to one specific execution/run.",
         default_retention_days=30, default_importance=0.3, decay_rate=0.1, is_persistent=False, summarize_after_tokens=None, max_entries_per_scope=None),
    dict(key=MemoryType.KNOWLEDGE.value, name="Knowledge Memory", description="Agent-facing recall backed by the curated Knowledge Platform.",
         default_retention_days=None, default_importance=0.8, decay_rate=0.002, is_persistent=True, summarize_after_tokens=None, max_entries_per_scope=None),
]


async def seed_builtin_memory_types(repos: RepositoryRegistry) -> list[MemoryTypePolicyModel]:
    created: list[MemoryTypePolicyModel] = []
    for spec in BUILTIN_MEMORY_TYPE_POLICIES:
        existing = await repos.memory_type_policies.get_by_key(spec["key"])
        if existing is not None:
            created.append(existing)
            continue
        created.append(await repos.memory_type_policies.add(MemoryTypePolicyModel(**spec, is_builtin=True)))
    return created
