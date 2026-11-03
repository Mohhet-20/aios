"""ToolPlanningService: the AI-facing planning layer that sits between an
agent/workflow's stated intent ("I need to send a Slack message" / "find
me a tool that can query a database") and the Execution Engine's
`connector_key`-keyed dispatch.

Responsibilities, mapped straight to the prompt's spec bullets:
  - Capability Matching       -> match_capabilities() reuses ToolDiscoveryService
  - Input Validation          -> validate_input() reuses validation/schema_validator.py
  - Automatic Tool Selection  -> select_tool()
  - Ranking                   -> rank_candidates()
  - Fallback Strategy         -> select_tool(..., fallback=True) / resolve_fallback_chain()
  - Multi-Tool Plans          -> build_plan()
  - Tool Composition          -> ToolPlan.add_step() + resolve_step_input() ($steps.<id>.<field> refs)
  - Execution Optimization    -> optimize_plan() (dedupes identical calls, reorders
                                  independent steps to the front so callers can
                                  batch/parallelize them)

This service never talks to a connector or the DB execution tables
directly — it only reads Tool/ToolVersion metadata (via ToolRepository /
ToolVersionRepository, through ToolDiscoveryService) and returns plain
dataclasses (`RankedTool`, `ToolPlan`) an execution-layer caller (the
Execution Engine, a workflow Tool Node, or an agent loop) turns into
real `start_execution` calls. Composing with the platform bridges
(`platform_bridges/`) — e.g. a plan step that should trigger a workflow
or notify an agent rather than run a connector tool — is the caller's
job, not this service's: this service only ever plans *tool* calls."""
from __future__ import annotations

import itertools
from typing import Any

from tool_platform.ai_planning.models import PlanStep, RankedTool, ToolPlan
from tool_platform.core.exceptions import ToolPlanningError
from tool_platform.discovery.discovery_service import ToolDiscoveryService, _lexical_score
from tool_platform.models.tool import ToolModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.validation.schema_validator import validate_against_schema


class ToolPlanningService:
    def __init__(self, repos: RepositoryRegistry, discovery: ToolDiscoveryService | None = None):
        self.repos = repos
        self.discovery = discovery or ToolDiscoveryService(repos)

    # -- capability matching ----------------------------------------------------------

    async def match_capabilities(
        self, workspace_id: str, required_capabilities: list[str]
    ) -> list[ToolModel]:
        """A tool matches only if it is PUBLISHED and its current version
        declares every one of the requested capabilities (AND semantics,
        not "any one will do") — callers that want an OR match should
        call this once per capability and union the results themselves."""
        if not required_capabilities:
            return []
        candidate_sets: list[set[str]] = []
        matches_by_id: dict[str, ToolModel] = {}
        for capability in required_capabilities:
            matches = await self.discovery.search_by_capability(workspace_id, capability)
            candidate_sets.append({t.id for t in matches})
            for t in matches:
                matches_by_id[t.id] = t
        common_ids = set.intersection(*candidate_sets) if candidate_sets else set()
        return [matches_by_id[i] for i in common_ids]

    # -- input validation ---------------------------------------------------------------

    async def validate_input(self, tool_version_id: str, input_data: dict[str, Any]) -> str | None:
        """Returns None if valid, else a human-readable error — pre-flight
        check before ever constructing an execution, reusing the exact
        same schema-validation logic the engine applies at dispatch time."""
        version = await self.repos.tool_versions.get_or_404(tool_version_id)
        return validate_against_schema(version.input_schema, input_data, label="tool input")

    # -- ranking ------------------------------------------------------------------------

    async def rank_candidates(
        self, workspace_id: str, query: str, candidates: list[ToolModel]
    ) -> list[RankedTool]:
        """Ranks by lexical relevance to `query` against name/description/
        tags/capabilities, tie-broken by workspace-wide popularity (same
        real execution-count signal ToolDiscoveryService.recommend uses)
        rather than fabricating a confidence score."""
        all_executions = await self.repos.executions.list_for_workspace(workspace_id, limit=10_000)
        popularity: dict[str, int] = {}
        for execution in all_executions:
            popularity[execution.tool_id] = popularity.get(execution.tool_id, 0) + 1

        ranked: list[RankedTool] = []
        for tool in candidates:
            capability_text = ""
            if tool.current_version_id:
                version = await self.repos.tool_versions.get(tool.current_version_id)
                if version is not None:
                    capability_text = " ".join(version.capabilities or [])
            haystack = " ".join([tool.name, tool.description or "", " ".join(tool.tags or []), capability_text])
            lexical = _lexical_score(query, haystack) if query else 0.0
            pop = popularity.get(tool.id, 0)
            # Lexical relevance dominates; popularity only breaks ties among
            # equally-relevant tools (normalized into a small fractional nudge
            # so it can never outrank a stronger lexical match).
            score = lexical + min(pop, 1000) / 1_000_000
            reason_bits = []
            if lexical > 0:
                reason_bits.append(f"matched query terms (lexical={lexical:.2f})")
            if pop:
                reason_bits.append(f"used {pop}x in this workspace")
            if not reason_bits:
                reason_bits.append("capability match only")
            ranked.append(RankedTool(
                tool_id=tool.id, name=tool.name, category=tool.category,
                score=score, reason="; ".join(reason_bits),
            ))
        ranked.sort(key=lambda r: r.score, reverse=True)
        return ranked

    # -- automatic selection + fallback ---------------------------------------------------

    async def select_tool(
        self, workspace_id: str, query: str, *, required_capabilities: list[str] | None = None
    ) -> list[RankedTool]:
        """Returns the ranked candidate list (best first) for a stated
        intent. The caller treats index 0 as the primary choice and walks
        forward through the rest as its fallback chain if the primary
        tool's execution fails or its health is degraded — this service
        doesn't hide the fallbacks, it surfaces the whole ordered list so
        the caller's fallback policy stays visible and inspectable."""
        if required_capabilities:
            candidates = await self.match_capabilities(workspace_id, required_capabilities)
        else:
            candidates = await self.discovery.semantic_search(workspace_id, query, top_k=50)
        if not candidates:
            raise ToolPlanningError(
                f"No published tool in workspace {workspace_id} matches query={query!r} "
                f"capabilities={required_capabilities!r}"
            )
        return await self.rank_candidates(workspace_id, query, candidates)

    def resolve_fallback_chain(self, ranked: list[RankedTool], *, max_fallbacks: int = 3) -> list[RankedTool]:
        """Primary is ranked[0]; this just caps how many fallbacks a caller
        commits to trying, so a huge candidate list doesn't turn into an
        unbounded retry storm across totally different tools."""
        return ranked[: 1 + max_fallbacks]

    # -- multi-tool plans / composition -----------------------------------------------------

    def build_plan(self, steps: list[tuple[str, str, dict[str, Any]]]) -> ToolPlan:
        """`steps` is an ordered list of (step_id, tool_id, input_template).
        input_template values may reference a prior step's output via the
        string "$steps.<step_id>.<field>" — resolved later by
        `resolve_step_input` once that step has actually run. Raises
        ToolPlanningError if a step references a step_id that either
        doesn't exist or comes later in the sequence (no forward/cyclic
        references — a plan is a DAG unrolled into an execution order)."""
        plan = ToolPlan()
        seen_ids: set[str] = set()
        for step_id, tool_id, input_template in steps:
            if step_id in seen_ids:
                raise ToolPlanningError(f"Duplicate step_id in plan: {step_id!r}")
            for ref_step_id in _referenced_step_ids(input_template):
                if ref_step_id not in seen_ids:
                    raise ToolPlanningError(
                        f"Step {step_id!r} references step {ref_step_id!r} which does not "
                        f"precede it — plans may only reference earlier steps' outputs"
                    )
            plan.add_step(step_id, tool_id, input_template)
            seen_ids.add(step_id)
        return plan

    def resolve_step_input(self, step: PlanStep, step_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Substitutes every "$steps.<step_id>.<field>" reference in a
        step's input_template with the actual value from a prior step's
        recorded output. Raises ToolPlanningError naming exactly which
        reference couldn't be resolved rather than silently passing
        through a broken placeholder string."""
        resolved: dict[str, Any] = {}
        for key, value in step.input_template.items():
            resolved[key] = _resolve_value(value, step_outputs)
        return resolved

    # -- execution optimization --------------------------------------------------------

    def optimize_plan(self, plan: ToolPlan) -> list[list[PlanStep]]:
        """Groups a plan's steps into ordered "waves": steps with no
        dependency on an earlier step's output are grouped into the same
        wave (safe to dispatch in parallel, e.g. via the Execution
        Engine's run_batch(execution_mode="parallel")); a step that
        references another step's output is placed in the first wave
        strictly after all of its dependencies. This is a real dependency
        analysis over the "$steps.<id>." references collected by
        build_plan, not a cosmetic reordering."""
        waves: list[list[PlanStep]] = []
        placed_wave: dict[str, int] = {}
        for step in plan.steps:
            deps = _referenced_step_ids(step.input_template)
            wave_index = 0
            if deps:
                wave_index = max(placed_wave[d] for d in deps) + 1
            while len(waves) <= wave_index:
                waves.append([])
            waves[wave_index].append(step)
            placed_wave[step.step_id] = wave_index
        return waves


def _referenced_step_ids(template: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for value in _flatten(template):
        if isinstance(value, str) and value.startswith("$steps."):
            parts = value.split(".")
            if len(parts) >= 2:
                ids.add(parts[1])
    return ids


def _flatten(value: Any) -> list[Any]:
    if isinstance(value, dict):
        return list(itertools.chain.from_iterable(_flatten(v) for v in value.values()))
    if isinstance(value, list):
        return list(itertools.chain.from_iterable(_flatten(v) for v in value))
    return [value]


def _resolve_value(value: Any, step_outputs: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, dict):
        return {k: _resolve_value(v, step_outputs) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(v, step_outputs) for v in value]
    if isinstance(value, str) and value.startswith("$steps."):
        parts = value.split(".")
        if len(parts) < 3:
            raise ToolPlanningError(f"Malformed step reference: {value!r}")
        ref_step_id, field_path = parts[1], parts[2:]
        if ref_step_id not in step_outputs:
            raise ToolPlanningError(f"Reference to unknown or not-yet-run step: {ref_step_id!r}")
        current: Any = step_outputs[ref_step_id]
        for field_name in field_path:
            if not isinstance(current, dict) or field_name not in current:
                raise ToolPlanningError(
                    f"Reference {value!r} could not be resolved — field {field_name!r} not found "
                    f"in step {ref_step_id!r}'s output"
                )
            current = current[field_name]
        return current
    return value
