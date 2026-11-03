"""Security & Governance: RBAC role grants, row/column-level security
rules, the audit log, and data lineage traversal."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from analytics_platform.an_api.serialization import to_dict, to_dict_list
from analytics_platform.dependencies.dependencies import (
    get_audit_log_service,
    get_column_level_security_service,
    get_current_tenant_id,
    get_data_lineage_service,
    get_rbac_service,
    get_row_level_security_service,
)
from analytics_platform.security.audit_service import AuditLogService
from analytics_platform.security.column_level_security_service import ColumnLevelSecurityService
from analytics_platform.security.lineage_service import DataLineageService
from analytics_platform.security.rbac_service import AnalyticsRbacService
from analytics_platform.security.row_level_security_service import RowLevelSecurityService

router = APIRouter(prefix="/roles", tags=["security"])
rls_router = APIRouter(prefix="/row-level-rules", tags=["security"])
cls_router = APIRouter(prefix="/column-level-rules", tags=["security"])
audit_router = APIRouter(prefix="/audit-log", tags=["security"])
lineage_router = APIRouter(prefix="/lineage", tags=["security"])


class GrantRoleRequest(BaseModel):
    principal_id: str
    role_level: str
    scope: str | None = None


@router.post("", status_code=201)
async def grant_role(
    body: GrantRoleRequest, tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsRbacService = Depends(get_rbac_service),
):
    return to_dict(await service.grant_role(tenant_id, body.principal_id, role_level=body.role_level, scope=body.scope))


@router.get("")
async def list_roles(
    tenant_id: str = Depends(get_current_tenant_id), service: AnalyticsRbacService = Depends(get_rbac_service),
):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.get("/{principal_id}")
async def get_role(
    principal_id: str, scope: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: AnalyticsRbacService = Depends(get_rbac_service),
):
    return {"role_level": await service.get_role(tenant_id, principal_id, scope=scope)}


class SetRowLevelRuleRequest(BaseModel):
    resource_type: str
    mode: str = "tenant_scoped"
    rule_expression: dict | None = None


@rls_router.post("", status_code=201)
async def set_row_level_rule(
    body: SetRowLevelRuleRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: RowLevelSecurityService = Depends(get_row_level_security_service),
):
    return to_dict(await service.set_rule(tenant_id, body.resource_type, mode=body.mode, rule_expression=body.rule_expression))


@rls_router.get("/{resource_type}")
async def get_row_level_rule(
    resource_type: str, tenant_id: str = Depends(get_current_tenant_id),
    service: RowLevelSecurityService = Depends(get_row_level_security_service),
):
    return to_dict(await service.get_rule(tenant_id, resource_type))


class SetColumnLevelRuleRequest(BaseModel):
    resource_type: str
    restricted_columns: list[str]
    allowed_roles: list[str]


@cls_router.post("", status_code=201)
async def set_column_level_rule(
    body: SetColumnLevelRuleRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ColumnLevelSecurityService = Depends(get_column_level_security_service),
):
    return to_dict(
        await service.set_rule(tenant_id, body.resource_type, restricted_columns=body.restricted_columns, allowed_roles=body.allowed_roles)
    )


@cls_router.get("/{resource_type}")
async def get_column_level_rule(
    resource_type: str, tenant_id: str = Depends(get_current_tenant_id),
    service: ColumnLevelSecurityService = Depends(get_column_level_security_service),
):
    return to_dict(await service.get_rule(tenant_id, resource_type))


class RecordAuditEntryRequest(BaseModel):
    action_type: str
    resource_type: str
    actor_id: str | None = None
    resource_id: str | None = None
    details: dict | None = None


@audit_router.post("", status_code=201)
async def record_audit_entry(
    body: RecordAuditEntryRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: AuditLogService = Depends(get_audit_log_service),
):
    return to_dict(await service.record(tenant_id, **body.model_dump()))


@audit_router.get("")
async def list_audit_entries(
    action_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: AuditLogService = Depends(get_audit_log_service),
):
    return to_dict_list(await service.list_recent(tenant_id, action_type=action_type))


class RecordLineageEdgeRequest(BaseModel):
    source_ref: str
    target_ref: str
    stage_type: str = "transform"
    transform_description: str | None = None


@lineage_router.post("/edges", status_code=201)
async def record_lineage_edge(
    body: RecordLineageEdgeRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: DataLineageService = Depends(get_data_lineage_service),
):
    return to_dict(await service.record_edge(tenant_id, **body.model_dump()))


@lineage_router.get("/upstream")
async def trace_upstream(
    ref: str, tenant_id: str = Depends(get_current_tenant_id), service: DataLineageService = Depends(get_data_lineage_service),
):
    return await service.trace_upstream(tenant_id, ref)


@lineage_router.get("/downstream")
async def trace_downstream(
    ref: str, tenant_id: str = Depends(get_current_tenant_id), service: DataLineageService = Depends(get_data_lineage_service),
):
    return await service.trace_downstream(tenant_id, ref)
