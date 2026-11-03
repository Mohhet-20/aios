"""Prompt Testing framework: single/batch/regression execution against a
prompt version, assertion-based pass/fail, and latency/token/cost
threshold validation — everything persisted as a TestRun + TestResults so
history/regression trends are queryable later.
"""
from __future__ import annotations

from dataclasses import dataclass, field


from ai_core.bootstrap import AICoreContext

from prompt_platform.domain.enums import RunStatus, TestRunType
from prompt_platform.models.testing import GoldenTestCaseModel, TestResultModel, TestRunModel
from prompt_platform.prompt_engine.render_execute import render_and_execute
from prompt_platform.prompt_observability.observability_service import ObservabilityService
from prompt_platform.prompt_testing.assertions import evaluate_all
from prompt_platform.repositories.registry import RepositoryRegistry
from prompt_platform.clock import utc_now


@dataclass
class PromptTestCase:
    variables: dict = field(default_factory=dict)
    expected_output: str | None = None
    assertions: list[dict] = field(default_factory=list)
    max_latency_ms: float | None = None
    max_cost_usd: float | None = None
    golden_test_case_id: str | None = None

    def resolved_assertions(self) -> list[dict]:
        if self.assertions:
            return self.assertions
        if self.expected_output:
            return [{"type": "contains", "value": self.expected_output}]
        return []


class PromptTestingService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext):
        self.repos = repos
        self.ai_core = ai_core
        self.observability = ObservabilityService(repos)

    async def _evaluate_case(self, version, case: PromptTestCase) -> TestResultModel:
        rendered_text, response = await render_and_execute(
            self.ai_core, version, case.variables, observability=self.observability,
            prompt_id=version.prompt_id, version_id=version.id, source="test",
        )
        failures = evaluate_all(case.resolved_assertions(), response.content)

        if case.max_latency_ms is not None and response.execution.latency_ms > case.max_latency_ms:
            failures.append(f"latency {response.execution.latency_ms:.1f}ms exceeded max {case.max_latency_ms}ms")
        if case.max_cost_usd is not None and response.cost.total_cost_usd > case.max_cost_usd:
            failures.append(f"cost ${response.cost.total_cost_usd:.4f} exceeded max ${case.max_cost_usd}")

        return TestResultModel(
            golden_test_case_id=case.golden_test_case_id,
            rendered_prompt=rendered_text,
            model_used=response.execution.model,
            provider_used=response.execution.provider,
            response_text=response.content,
            passed=not failures,
            failure_reasons=failures,
            latency_ms=response.execution.latency_ms,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=response.cost.total_cost_usd,
        )

    async def _run(self, prompt_id: str, version_id: str, run_type: TestRunType, cases: list[PromptTestCase], triggered_by: str) -> TestRunModel:
        run = await self.repos.test_runs.add(
            TestRunModel(prompt_id=prompt_id, version_id=version_id, run_type=run_type.value, status=RunStatus.RUNNING.value, triggered_by=triggered_by)
        )
        version = await self.repos.versions.get_or_404(version_id)

        results: list[TestResultModel] = []
        for case in cases:
            result = await self._evaluate_case(version, case)
            result.test_run_id = run.id
            results.append(await self.repos.test_results.add(result))

        passed = sum(1 for r in results if r.passed)
        total = len(results)
        run.status = RunStatus.COMPLETED.value
        run.completed_at = utc_now()
        run.summary = {
            "total": total, "passed": passed, "failed": total - passed,
            "pass_rate": round(passed / total * 100, 2) if total else 0.0,
        }
        return await self.repos.test_runs.update(run)

    async def run_single(self, prompt_id: str, version_id: str, *, variables: dict, expected_output: str | None = None, assertions: list[dict] | None = None, triggered_by: str) -> TestRunModel:
        case = PromptTestCase(variables=variables, expected_output=expected_output, assertions=assertions or [])
        return await self._run(prompt_id, version_id, TestRunType.SINGLE, [case], triggered_by)

    async def run_batch(self, prompt_id: str, version_id: str, cases: list[PromptTestCase], triggered_by: str) -> TestRunModel:
        return await self._run(prompt_id, version_id, TestRunType.BATCH, cases, triggered_by)

    async def run_regression(self, prompt_id: str, version_id: str, triggered_by: str) -> TestRunModel:
        golden_cases = await self.repos.golden_test_cases.list_for_prompt(prompt_id)
        cases = [
            PromptTestCase(
                variables=gc.input_variables, expected_output=gc.expected_output, assertions=gc.assertions,
                max_latency_ms=gc.max_latency_ms, max_cost_usd=gc.max_cost_usd, golden_test_case_id=gc.id,
            )
            for gc in golden_cases
        ]
        return await self._run(prompt_id, version_id, TestRunType.REGRESSION, cases, triggered_by)

    async def get_results(self, test_run_id: str) -> list[TestResultModel]:
        return await self.repos.test_results.list_for_run(test_run_id)

    async def create_golden_test_case(self, prompt_id: str, *, name: str, input_variables: dict, expected_output: str | None = None, assertions: list[dict] | None = None, max_latency_ms: float | None = None, max_cost_usd: float | None = None) -> GoldenTestCaseModel:
        return await self.repos.golden_test_cases.add(
            GoldenTestCaseModel(
                prompt_id=prompt_id, name=name, input_variables=input_variables, expected_output=expected_output,
                assertions=assertions or [], max_latency_ms=max_latency_ms, max_cost_usd=max_cost_usd,
            )
        )
