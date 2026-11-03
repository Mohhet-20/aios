"""Package Registry: generic catalog spanning sdk/plugin/connector/
template/schema package types, plus dependency graph resolution."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_package_dependency_service,
    get_package_registry_service,
)
from developer_platform.dev_api.serialization import to_dict, to_dict_list
from developer_platform.registry_platform.dependency_service import PackageDependencyService
from developer_platform.registry_platform.package_service import PackageRegistryService

router = APIRouter(prefix="/registry/packages", tags=["registry-platform"])


class RegisterPackageRequest(BaseModel):
    name: str
    package_type: str
    owner_id: str | None = None
    description: str | None = None


@router.post("", status_code=201)
async def register_package(
    body: RegisterPackageRequest, tenant_id: str = Depends(get_current_tenant_id), service: PackageRegistryService = Depends(get_package_registry_service),
):
    return to_dict(await service.register_package(tenant_id, **body.model_dump()))


class PublishVersionRequest(BaseModel):
    version: str
    language: str | None = None
    storage_uri: str | None = None
    checksum: str | None = None
    dependencies: list | None = None


@router.post("/{package_id}/versions", status_code=201)
async def publish_package_version(
    package_id: str, body: PublishVersionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PackageRegistryService = Depends(get_package_registry_service),
):
    return to_dict(await service.publish_version(tenant_id, package_id, **body.model_dump()))


class DeprecateVersionRequest(BaseModel):
    version: str


@router.post("/{package_id}/deprecate")
async def deprecate_package_version(
    package_id: str, body: DeprecateVersionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PackageRegistryService = Depends(get_package_registry_service),
):
    result = await service.deprecate_version(tenant_id, package_id, version=body.version)
    payload = to_dict(result.version)
    payload["recommended_removal_at"] = result.recommended_removal_at.isoformat()
    return payload


@router.get("/{package_id}/versions")
async def list_package_versions(
    package_id: str, tenant_id: str = Depends(get_current_tenant_id), service: PackageRegistryService = Depends(get_package_registry_service),
):
    return to_dict_list(await service.list_versions(tenant_id, package_id))


@router.get("/by-type/{package_type}")
async def list_packages_by_type(
    package_type: str, tenant_id: str = Depends(get_current_tenant_id), service: PackageRegistryService = Depends(get_package_registry_service),
):
    return to_dict_list(await service.list_by_type(tenant_id, package_type))


class AddDependencyRequest(BaseModel):
    version: str
    depends_on_name: str
    depends_on_type: str
    constraint: str = "*"


@router.post("/{package_id}/dependencies")
async def add_package_dependency(
    package_id: str, body: AddDependencyRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: PackageDependencyService = Depends(get_package_dependency_service),
):
    return to_dict(await service.add_dependency(tenant_id, package_id, **body.model_dump()))


@router.get("/{package_id}/dependencies/resolve")
async def resolve_package_dependencies(
    package_id: str, version: str, tenant_id: str = Depends(get_current_tenant_id),
    service: PackageDependencyService = Depends(get_package_dependency_service),
):
    return to_dict_list(await service.resolve_dependencies(tenant_id, package_id, version=version))
