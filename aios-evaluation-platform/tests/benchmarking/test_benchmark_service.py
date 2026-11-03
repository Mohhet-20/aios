import pytest

from eval_platform.core.exceptions import BenchmarkError
from eval_platform.core.pagination import PaginationParams


@pytest.mark.asyncio
async def test_create_benchmark(benchmark_service, workspace):
    benchmark = await benchmark_service.create_benchmark(
        workspace.id, name="Prompt AB", owner_id="u1", benchmark_type="prompt", mode="ab_test", organization_id="org-1",
    )
    assert benchmark.slug == "prompt-ab"
    assert benchmark.benchmark_type == "prompt"


@pytest.mark.asyncio
async def test_create_benchmark_rejects_unknown_type(benchmark_service, workspace):
    with pytest.raises(BenchmarkError):
        await benchmark_service.create_benchmark(
            workspace.id, name="X", owner_id="u1", benchmark_type="not_real", mode="single", organization_id="org-1",
        )


@pytest.mark.asyncio
async def test_create_benchmark_rejects_unknown_mode(benchmark_service, workspace):
    with pytest.raises(BenchmarkError):
        await benchmark_service.create_benchmark(
            workspace.id, name="X", owner_id="u1", benchmark_type="model", mode="not_real", organization_id="org-1",
        )


@pytest.mark.asyncio
async def test_create_benchmark_duplicate_slug_raises(benchmark_service, workspace):
    await benchmark_service.create_benchmark(workspace.id, name="D1", owner_id="u1", benchmark_type="model", mode="single", organization_id="org-1")
    with pytest.raises(BenchmarkError):
        await benchmark_service.create_benchmark(workspace.id, name="D1", owner_id="u1", benchmark_type="model", mode="single", organization_id="org-1")


@pytest.mark.asyncio
async def test_update_benchmark_rejects_unknown_field(benchmark_service, workspace):
    benchmark = await benchmark_service.create_benchmark(workspace.id, name="D1", owner_id="u1", benchmark_type="model", mode="single", organization_id="org-1")
    with pytest.raises(BenchmarkError):
        await benchmark_service.update_benchmark(benchmark.id, benchmark_type="prompt")


@pytest.mark.asyncio
async def test_list_and_delete_benchmark(benchmark_service, workspace):
    await benchmark_service.create_benchmark(workspace.id, name="D1", owner_id="u1", benchmark_type="model", mode="single", organization_id="org-1")
    b2 = await benchmark_service.create_benchmark(workspace.id, name="D2", owner_id="u1", benchmark_type="model", mode="single", organization_id="org-1")

    page = await benchmark_service.list_benchmarks(workspace.id, PaginationParams(page=1, page_size=10))
    assert page.total == 2

    await benchmark_service.delete_benchmark(b2.id)
    page = await benchmark_service.list_benchmarks(workspace.id, PaginationParams(page=1, page_size=10))
    assert page.total == 1
