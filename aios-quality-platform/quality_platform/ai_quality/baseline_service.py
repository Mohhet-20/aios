"""Baseline management: one score per (tenant, dimension, subject_ref)
that regression scans compare fresh evaluations against. `set_baseline`
is an upsert behind a commit-spanning `asyncio.Lock` keyed on
(tenant_id, dimension, subject_ref) — the same get-or-create-under-lock
pattern established across every prior AIOS platform, including the
mid-lock commit needed so a waiting caller's read can't observe a
still-uncommitted insert from a separate DB connection."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import AiQualityBaselineNotFoundError, UnsupportedAiQualityDimensionError
from quality_platform.models.ai_quality import AiQualityBaselineModel
from quality_platform.repositories.registry import RepositoryRegistry


class BaselineService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    def _validate_dimension(self, dimension: str) -> None:
        if dimension not in self.settings.ai_quality_dimensions:
            raise UnsupportedAiQualityDimensionError(f"Unsupported AI quality dimension '{dimension}'")

    async def get_baseline_or_404(self, tenant_id: str, dimension: str, subject_ref: str) -> AiQualityBaselineModel:
        baseline = await self.repos.ai_quality_baselines.get_for_subject(tenant_id, dimension, subject_ref)
        if baseline is None:
            raise AiQualityBaselineNotFoundError(
                f"No baseline for dimension '{dimension}' subject '{subject_ref}' (tenant '{tenant_id}')"
            )
        return baseline

    async def set_baseline(
        self, tenant_id: str, dimension: str, subject_ref: str, *, baseline_score: float, sample_size: int
    ) -> AiQualityBaselineModel:
        self._validate_dimension(dimension)
        lock_key = f"{tenant_id}:{dimension}:{subject_ref}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.ai_quality_baselines.get_for_subject(tenant_id, dimension, subject_ref)
            if existing is not None:
                existing.baseline_score = baseline_score
                existing.sample_size = sample_size
                existing = await self.repos.ai_quality_baselines.update(existing)
                await self.repos.session.commit()
                return existing
            baseline = AiQualityBaselineModel(
                tenant_id=tenant_id, dimension=dimension, subject_ref=subject_ref,
                baseline_score=baseline_score, sample_size=sample_size,
            )
            baseline = await self.repos.ai_quality_baselines.add(baseline)
            await self.repos.session.commit()
            return baseline
