"""Load balancing: picks one healthy instance per call according to a
per-service pool strategy. `round_robin` and `weighted` are real,
stateful selections (round-robin advances a persisted cursor;
weighted does cumulative-weight selection over an injectable random
source for deterministic tests). `least_connections` is a disclosed
approximation — this control plane doesn't do real-time per-instance
connection accounting, so it falls back to round-robin selection
rather than pretending to track live connection counts it doesn't
have."""
from __future__ import annotations

import random
from collections.abc import Callable

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import NoHealthyInstancesError, ValidationError
from gateway_platform.domain.enums import InstanceStatus, LoadBalancingStrategy
from gateway_platform.models.mesh import LoadBalancerPoolModel, ServiceInstanceModel
from gateway_platform.repositories.registry import RepositoryRegistry


class LoadBalancerService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None, rand: Callable[[], float] = random.random):
        self.repos = repos
        self.settings = settings or get_settings()
        self._rand = rand

    def _assert_valid_strategy(self, strategy: str) -> None:
        if strategy not in {s.value for s in LoadBalancingStrategy}:
            raise ValidationError(f"'{strategy}' is not a recognized load balancing strategy")

    async def configure_pool(self, tenant_id: str, service_id: str, *, strategy: str | None = None) -> LoadBalancerPoolModel:
        strategy = strategy or self.settings.mesh_default_load_balancing_strategy
        self._assert_valid_strategy(strategy)
        pool = await self.repos.load_balancer_pools.get_for_service(tenant_id, service_id)
        if pool is not None:
            pool.strategy = strategy
            return await self.repos.load_balancer_pools.update(pool)
        pool = LoadBalancerPoolModel(tenant_id=tenant_id, service_id=service_id, strategy=strategy, last_index=0)
        return await self.repos.load_balancer_pools.add(pool)

    async def select_instance(self, tenant_id: str, service_id: str) -> ServiceInstanceModel:
        instances = await self.repos.service_instances.list_for_service(
            tenant_id, service_id, status=InstanceStatus.ACTIVE.value,
        )
        if not instances:
            raise NoHealthyInstancesError(f"no healthy instances available for service '{service_id}'")

        pool = await self.repos.load_balancer_pools.get_for_service(tenant_id, service_id)
        strategy = pool.strategy if pool is not None else self.settings.mesh_default_load_balancing_strategy

        if strategy == LoadBalancingStrategy.WEIGHTED.value:
            return self._select_weighted(instances)
        if strategy == LoadBalancingStrategy.RANDOM.value:
            return instances[int(self._rand() * len(instances)) % len(instances)]
        # round_robin and least_connections (approximated) both advance the shared cursor
        return await self._select_round_robin(tenant_id, service_id, instances, pool)

    def _select_weighted(self, instances: list[ServiceInstanceModel]) -> ServiceInstanceModel:
        total_weight = sum(max(i.weight, 1) for i in instances)
        target = self._rand() * total_weight
        cumulative = 0.0
        for instance in instances:
            cumulative += max(instance.weight, 1)
            if target < cumulative:
                return instance
        return instances[-1]

    async def _select_round_robin(
        self, tenant_id: str, service_id: str, instances: list[ServiceInstanceModel], pool: LoadBalancerPoolModel | None,
    ) -> ServiceInstanceModel:
        if pool is None:
            pool = await self.configure_pool(tenant_id, service_id)
        index = pool.last_index % len(instances)
        pool.last_index = (pool.last_index + 1) % len(instances)
        await self.repos.load_balancer_pools.update(pool)
        return instances[index]
