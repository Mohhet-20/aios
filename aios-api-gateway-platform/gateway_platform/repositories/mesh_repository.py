from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.mesh import (
    CircuitBreakerModel,
    HealthCheckResultModel,
    LoadBalancerPoolModel,
    ServiceInstanceModel,
    ServiceRegistrationModel,
)
from gateway_platform.repositories.base import SQLAlchemyRepository


class ServiceRegistrationRepository(SQLAlchemyRepository[ServiceRegistrationModel]):
    model = ServiceRegistrationModel

    async def get_by_name(self, tenant_id: str, name: str) -> ServiceRegistrationModel | None:
        stmt = select(ServiceRegistrationModel).where(
            ServiceRegistrationModel.tenant_id == tenant_id, ServiceRegistrationModel.name == name,
            ServiceRegistrationModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[ServiceRegistrationModel]:
        stmt = select(ServiceRegistrationModel).where(
            ServiceRegistrationModel.tenant_id == tenant_id, ServiceRegistrationModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ServiceInstanceRepository(SQLAlchemyRepository[ServiceInstanceModel]):
    model = ServiceInstanceModel

    async def list_for_service(self, tenant_id: str, service_id: str, *, status: str | None = None) -> list[ServiceInstanceModel]:
        stmt = select(ServiceInstanceModel).where(
            ServiceInstanceModel.tenant_id == tenant_id, ServiceInstanceModel.service_id == service_id,
            ServiceInstanceModel.is_deleted.is_(False),
        )
        if status:
            stmt = stmt.where(ServiceInstanceModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())


class LoadBalancerPoolRepository(SQLAlchemyRepository[LoadBalancerPoolModel]):
    model = LoadBalancerPoolModel

    async def get_for_service(self, tenant_id: str, service_id: str) -> LoadBalancerPoolModel | None:
        stmt = select(LoadBalancerPoolModel).where(
            LoadBalancerPoolModel.tenant_id == tenant_id, LoadBalancerPoolModel.service_id == service_id,
        )
        return (await self.session.execute(stmt)).scalars().first()


class CircuitBreakerRepository(SQLAlchemyRepository[CircuitBreakerModel]):
    model = CircuitBreakerModel

    async def get_for_service(self, tenant_id: str, service_id: str) -> CircuitBreakerModel | None:
        stmt = select(CircuitBreakerModel).where(
            CircuitBreakerModel.tenant_id == tenant_id, CircuitBreakerModel.service_id == service_id,
        )
        return (await self.session.execute(stmt)).scalars().first()


class HealthCheckResultRepository(SQLAlchemyRepository[HealthCheckResultModel]):
    model = HealthCheckResultModel

    async def list_for_instance(self, tenant_id: str, instance_id: str, *, limit: int = 50) -> list[HealthCheckResultModel]:
        stmt = select(HealthCheckResultModel).where(
            HealthCheckResultModel.tenant_id == tenant_id, HealthCheckResultModel.instance_id == instance_id,
        ).order_by(HealthCheckResultModel.checked_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
