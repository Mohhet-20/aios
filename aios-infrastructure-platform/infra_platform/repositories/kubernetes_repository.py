from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.kubernetes import (
    AutoscalerConfigModel,
    ClusterModel,
    K8sResourceModel,
    NamespaceModel,
    NodePoolModel,
    ResourceQuotaModel,
)
from infra_platform.repositories.base import SQLAlchemyRepository


class ClusterRepository(SQLAlchemyRepository[ClusterModel]):
    model = ClusterModel

    async def list_for_tenant(self, tenant_id: str) -> list[ClusterModel]:
        stmt = select(ClusterModel).where(ClusterModel.tenant_id == tenant_id, ClusterModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class NodePoolRepository(SQLAlchemyRepository[NodePoolModel]):
    model = NodePoolModel

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[NodePoolModel]:
        stmt = select(NodePoolModel).where(NodePoolModel.tenant_id == tenant_id, NodePoolModel.cluster_id == cluster_id)
        return list((await self.session.execute(stmt)).scalars().all())


class NamespaceRepository(SQLAlchemyRepository[NamespaceModel]):
    model = NamespaceModel

    async def get_by_name(self, tenant_id: str, cluster_id: str, name: str) -> NamespaceModel | None:
        stmt = select(NamespaceModel).where(
            NamespaceModel.tenant_id == tenant_id, NamespaceModel.cluster_id == cluster_id, NamespaceModel.name == name
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[NamespaceModel]:
        stmt = select(NamespaceModel).where(NamespaceModel.tenant_id == tenant_id, NamespaceModel.cluster_id == cluster_id)
        return list((await self.session.execute(stmt)).scalars().all())


class K8sResourceRepository(SQLAlchemyRepository[K8sResourceModel]):
    model = K8sResourceModel

    async def list_for_namespace(self, tenant_id: str, cluster_id: str, namespace: str) -> list[K8sResourceModel]:
        stmt = select(K8sResourceModel).where(
            K8sResourceModel.tenant_id == tenant_id, K8sResourceModel.cluster_id == cluster_id, K8sResourceModel.namespace == namespace
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_kind_name(self, tenant_id: str, cluster_id: str, namespace: str, kind: str, name: str) -> K8sResourceModel | None:
        stmt = select(K8sResourceModel).where(
            K8sResourceModel.tenant_id == tenant_id, K8sResourceModel.cluster_id == cluster_id,
            K8sResourceModel.namespace == namespace, K8sResourceModel.kind == kind, K8sResourceModel.name == name,
        )
        return (await self.session.execute(stmt)).scalars().first()


class ResourceQuotaRepository(SQLAlchemyRepository[ResourceQuotaModel]):
    model = ResourceQuotaModel

    async def get_for_namespace(self, tenant_id: str, cluster_id: str, namespace: str) -> ResourceQuotaModel | None:
        stmt = select(ResourceQuotaModel).where(
            ResourceQuotaModel.tenant_id == tenant_id, ResourceQuotaModel.cluster_id == cluster_id, ResourceQuotaModel.namespace == namespace
        )
        return (await self.session.execute(stmt)).scalars().first()


class AutoscalerConfigRepository(SQLAlchemyRepository[AutoscalerConfigModel]):
    model = AutoscalerConfigModel

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[AutoscalerConfigModel]:
        stmt = select(AutoscalerConfigModel).where(AutoscalerConfigModel.tenant_id == tenant_id, AutoscalerConfigModel.cluster_id == cluster_id)
        return list((await self.session.execute(stmt)).scalars().all())
