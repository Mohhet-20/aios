"""Evaluation aggregate — tracks a single graded run of a prompt/agent/model
against a dataset, matching the Evaluation Engine design from the original architecture.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects.enums import EvaluationStatus

REGRESSION_THRESHOLD = 0.0  # any negative delta counts as a regression


@dataclass
class EvaluationRun:
    id: str
    workspace_id: str
    suite_name: str
    target_type: str  # "prompt_version" | "agent" | "model"
    target_id: str
    dataset_id: str
    status: EvaluationStatus
    total: int = 0
    passed: int = 0
    failed: int = 0
    score: float | None = None
    previous_score: float | None = None

    @property
    def is_regression(self) -> bool:
        if self.previous_score is None or self.score is None:
            return False
        return (self.score - self.previous_score) < REGRESSION_THRESHOLD

    def complete(self, passed: int, failed: int) -> None:
        self.passed = passed
        self.failed = failed
        self.total = passed + failed
        self.score = round((passed / self.total) * 100, 2) if self.total else 0.0
        self.status = EvaluationStatus.COMPLETED
