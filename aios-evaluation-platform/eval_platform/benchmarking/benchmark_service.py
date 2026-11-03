"""BenchmarkService: identity/ownership CRUD for a reusable comparison
setup (`BenchmarkModel`) bound to a dataset — model benchmarking,
prompt A/B/multivariate testing, or an agent/workflow comparison,
depending on `benchmark_type`/`mode`. Mirrors `DatasetService`'s shape;
the actual multi-candidate execution lives in `run_service.py`."""
from __future__ import annotations

from slugify import slugify

from eval_platform.core.exceptions import BenchmarkError
from eval_platform.core.pagination import Page, PaginationParams
from eval_platform.domain.enums import BenchmarkMode, BenchmarkType
from eval_platform.models.benchmark import BenchmarkModel
from eval_platform.repositories.registry import RepositoryRegistry

_VALID_TYPES = {t.value for t in BenchmarkType}
_VALID_MODES = {m.value for m in BenchmarkMode}


class BenchmarkService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_benchmark(
        self, workspace_id: str, *, name: str, owner_id: str, benchmark_type: str, mode: str, organization_id: str,
        dataset_id: str | None = None, slug: str | None = None, description: str | None = None,
        tags: list[str] | None = None, metric_keys: list[str] | None = None,
    ) -> BenchmarkModel:
        if benchmark_type not in _VALID_TYPES:
            raise BenchmarkError(f"unknown benchmark_type '{benchmark_type}' (must be one of {sorted(_VALID_TYPES)})")
        if mode not in _VALID_MODES:
            raise BenchmarkError(f"unknown mode '{mode}' (must be one of {sorted(_VALID_MODES)})")

        resolved_slug = slug or slugify(name)
        existing = await self.repos.benchmarks.get_by_slug(workspace_id, resolved_slug)
        if existing is not None:
            raise BenchmarkError(f"a benchmark with slug '{resolved_slug}' already exists in this workspace")

        return await self.repos.benchmarks.add(BenchmarkModel(
            workspace_id=workspace_id, organization_id=organization_id, name=name, slug=resolved_slug,
            description=description, owner_id=owner_id, benchmark_type=benchmark_type, mode=mode,
            dataset_id=dataset_id, tags=tags or [], metric_keys=metric_keys or [],
        ))

    async def get_benchmark(self, benchmark_id: str) -> BenchmarkModel:
        return await self.repos.benchmarks.get_or_404(benchmark_id)

    async def list_benchmarks(
        self, workspace_id: str, params: PaginationParams, *, benchmark_type: str | None = None
    ) -> Page[BenchmarkModel]:
        filters: dict = {"workspace_id": workspace_id}
        if benchmark_type:
            filters["benchmark_type"] = benchmark_type
        return await self.repos.benchmarks.paginated_list(params, filters=filters)

    async def update_benchmark(self, benchmark_id: str, **fields) -> BenchmarkModel:
        benchmark = await self.repos.benchmarks.get_or_404(benchmark_id)
        allowed = {"name", "description", "tags", "dataset_id", "metric_keys"}
        unknown = set(fields) - allowed
        if unknown:
            raise BenchmarkError(f"cannot update fields: {sorted(unknown)}")
        for key, value in fields.items():
            setattr(benchmark, key, value)
        return await self.repos.benchmarks.update(benchmark)

    async def delete_benchmark(self, benchmark_id: str) -> None:
        benchmark = await self.repos.benchmarks.get_or_404(benchmark_id)
        await self.repos.benchmarks.delete(benchmark)
