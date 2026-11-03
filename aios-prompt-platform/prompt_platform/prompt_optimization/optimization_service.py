"""Orchestrates prompt optimization: rule-based suggestions (always
available), LLM-backed automatic rewriting (quality/cost/latency
objectives), few-shot example selection, and applying an optimization's
result as a new draft PromptVersion via VersioningService. Every run and
its suggestions are persisted for auditability and later comparison.
"""
from __future__ import annotations


from ai_core.bootstrap import AICoreContext

from prompt_platform.core.exceptions import ValidationError
from prompt_platform.domain.enums import OptimizationCategory, OptimizationObjective, RunStatus
from prompt_platform.models.optimization import OptimizationRunModel, OptimizationSuggestionModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.prompt_engine.versioning_service import VersioningService
from prompt_platform.prompt_optimization import few_shot, llm_optimizer
from prompt_platform.prompt_optimization.heuristics import estimate_tokens
from prompt_platform.prompt_optimization.suggestion_engine import generate_rule_based_suggestions
from prompt_platform.repositories.registry import RepositoryRegistry
from prompt_platform.clock import utc_now


class OptimizationService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext, *, versioning_service: VersioningService | None = None):
        self.repos = repos
        self.ai_core = ai_core
        self.versioning_service = versioning_service or VersioningService(repos)

    # -- run bookkeeping -------------------------------------------------

    async def _start_run(self, prompt_id: str, version_id: str, objective: OptimizationObjective, triggered_by: str) -> OptimizationRunModel:
        return await self.repos.optimization_runs.add(
            OptimizationRunModel(
                prompt_id=prompt_id, version_id=version_id, objective=objective.value,
                status=RunStatus.RUNNING.value, triggered_by=triggered_by,
            )
        )

    async def _add_suggestion(self, run_id: str, s: dict) -> OptimizationSuggestionModel:
        return await self.repos.optimization_suggestions.add(
            OptimizationSuggestionModel(
                optimization_run_id=run_id, category=s["category"], title=s["title"], rationale=s["rationale"],
                original_text=s.get("original_text"), suggested_text=s.get("suggested_text"),
                estimated_impact=s.get("estimated_impact"),
            )
        )

    async def _complete_run(self, run: OptimizationRunModel, suggestions: list[dict], *, result_version_id: str | None = None) -> OptimizationRunModel:
        run.status = RunStatus.COMPLETED.value
        run.completed_at = utc_now()
        run.result_version_id = result_version_id
        categories = sorted({s["category"] for s in suggestions})
        run.summary = {"suggestion_count": len(suggestions), "categories": categories}
        return await self.repos.optimization_runs.update(run)

    # -- suggestions (rule-based, no LLM call) ----------------------------

    async def suggest(self, prompt_id: str, version_id: str, *, objective: OptimizationObjective = OptimizationObjective.QUALITY, triggered_by: str) -> OptimizationRunModel:
        version = await self.repos.versions.get_or_404(version_id)
        run = await self._start_run(prompt_id, version_id, objective, triggered_by)
        suggestions = generate_rule_based_suggestions(version, objective=objective, registry=self.ai_core.registry)
        for s in suggestions:
            await self._add_suggestion(run.id, s)
        return await self._complete_run(run, suggestions)

    # -- LLM-backed automatic rewriting -----------------------------------

    async def auto_optimize(
        self, prompt_id: str, version_id: str, *, objective: OptimizationObjective, actor_id: str, apply: bool = False
    ) -> OptimizationRunModel:
        version = await self.repos.versions.get_or_404(version_id)
        if not version.user_template:
            raise ValidationError("Version has no user_template to optimize")
        run = await self._start_run(prompt_id, version_id, objective, actor_id)

        original = version.user_template
        if objective == OptimizationObjective.QUALITY:
            rewritten = await llm_optimizer.refine_instructions(self.ai_core, original)
            category = OptimizationCategory.INSTRUCTION_CLARITY
            title = "LLM-refined instructions"
        elif objective in (OptimizationObjective.COST, OptimizationObjective.TOKEN_COUNT, OptimizationObjective.LATENCY):
            rewritten = await llm_optimizer.compress_prompt(self.ai_core, original)
            category = OptimizationCategory.COMPRESSION
            title = "LLM-compressed prompt"
        else:
            rewritten = await llm_optimizer.expand_prompt(self.ai_core, original)
            category = OptimizationCategory.EXPANSION
            title = "LLM-expanded prompt"

        before_tokens = estimate_tokens(original)
        after_tokens = estimate_tokens(rewritten)
        suggestion = {
            "category": category.value, "title": title,
            "rationale": f"Automatic {objective.value}-objective rewrite via the AI Core.",
            "original_text": original, "suggested_text": rewritten,
            "estimated_impact": {"tokens_before": before_tokens, "tokens_after": after_tokens, "token_delta": after_tokens - before_tokens},
        }
        suggestion_model = await self._add_suggestion(run.id, suggestion)

        result_version_id = None
        if apply:
            new_version = await self._apply(prompt_id, version, rewritten, actor_id)
            suggestion_model.applied = True
            await self.repos.optimization_suggestions.update(suggestion_model)
            result_version_id = new_version.id

        return await self._complete_run(run, [suggestion], result_version_id=result_version_id)

    # -- few-shot example selection ---------------------------------------

    async def optimize_few_shot(
        self, prompt_id: str, version_id: str, *, actor_id: str, max_examples: int = 3, apply: bool = False
    ) -> OptimizationRunModel:
        version = await self.repos.versions.get_or_404(version_id)
        run = await self._start_run(prompt_id, version_id, OptimizationObjective.QUALITY, actor_id)

        golden_cases = await self.repos.golden_test_cases.list_for_prompt(prompt_id)
        selected = few_shot.select_few_shot_examples(golden_cases, max_examples=max_examples)

        if not selected:
            suggestions: list[dict] = [{
                "category": OptimizationCategory.FEW_SHOT_EXAMPLES.value,
                "title": "No eligible golden test cases",
                "rationale": "No golden test case has an expected_output recorded, so no few-shot examples could be selected.",
                "original_text": None, "suggested_text": None, "estimated_impact": None,
            }]
            for s in suggestions:
                await self._add_suggestion(run.id, s)
            return await self._complete_run(run, suggestions)

        block = few_shot.build_few_shot_block(selected)
        new_template = f"{version.user_template.rstrip()}\n\n{block}" if version.user_template else block
        suggestion = {
            "category": OptimizationCategory.FEW_SHOT_EXAMPLES.value,
            "title": f"Add {len(selected)} few-shot example(s)",
            "rationale": f"Selected from golden test cases: {', '.join(c.name for c in selected)}.",
            "original_text": version.user_template, "suggested_text": new_template,
            "estimated_impact": {"examples_added": len(selected)},
        }
        suggestion_model = await self._add_suggestion(run.id, suggestion)

        result_version_id = None
        if apply:
            new_version = await self._apply(prompt_id, version, new_template, actor_id)
            suggestion_model.applied = True
            await self.repos.optimization_suggestions.update(suggestion_model)
            result_version_id = new_version.id

        return await self._complete_run(run, [suggestion], result_version_id=result_version_id)

    # -- applying a suggestion --------------------------------------------

    async def _apply(self, prompt_id: str, version: PromptVersionModel, new_user_template: str, actor_id: str) -> PromptVersionModel:
        return await self.versioning_service.create_version(
            prompt_id, user_template=new_user_template, actor_id=actor_id,
            system_template=version.system_template, developer_template=version.developer_template,
            variables_schema=version.variables_schema, parameters=version.parameters,
            parent_version_id=version.id,
        )

    async def apply_suggestion(self, suggestion_id: str, actor_id: str) -> PromptVersionModel:
        suggestion = await self.repos.optimization_suggestions.get_or_404(suggestion_id)
        if not suggestion.suggested_text:
            raise ValidationError("Suggestion has no suggested_text to apply")
        run = await self.repos.optimization_runs.get_or_404(suggestion.optimization_run_id)
        version = await self.repos.versions.get_or_404(run.version_id)
        new_version = await self._apply(run.prompt_id, version, suggestion.suggested_text, actor_id)
        suggestion.applied = True
        await self.repos.optimization_suggestions.update(suggestion)
        run.result_version_id = new_version.id
        await self.repos.optimization_runs.update(run)
        return new_version

    # -- listing ------------------------------------------------------------

    async def get_suggestions(self, run_id: str) -> list[OptimizationSuggestionModel]:
        return await self.repos.optimization_suggestions.list_for_run(run_id)

    async def list_runs(self, prompt_id: str) -> list[OptimizationRunModel]:
        return await self.repos.optimization_runs.list_for_prompt(prompt_id)
