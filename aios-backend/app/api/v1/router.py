"""Aggregates every v1 business router under one `APIRouter`. Health and
metrics are deliberately NOT included here — they're mounted at the
application root (unversioned, unprefixed) in `app.core.application_factory`
since infrastructure tooling (k8s probes, Prometheus) expects them at fixed
paths regardless of API version.
"""

from fastapi import APIRouter

from app.routers.v1 import (
    agents_router,
    audit_logs_router,
    auth_router,
    configuration_router,
    conversations_router,
    datasets_router,
    documents_router,
    embeddings_router,
    evaluations_router,
    experiments_router,
    inference_router,
    knowledge_router,
    memory_router,
    models_router,
    monitoring_router,
    notifications_router,
    observability_router,
    organizations_router,
    plugins_router,
    projects_router,
    prompts_router,
    reports_router,
    search_router,
    users_router,
    workflow_executions_router,
    workflows_router,
    workspaces_router,
)

api_router = APIRouter()

api_router.include_router(auth_router.router)
api_router.include_router(users_router.router)
api_router.include_router(organizations_router.router)
api_router.include_router(workspaces_router.router)
api_router.include_router(projects_router.router)
api_router.include_router(agents_router.router)
api_router.include_router(prompts_router.router)
api_router.include_router(workflows_router.router)
api_router.include_router(workflow_executions_router.router)
api_router.include_router(models_router.router)
api_router.include_router(inference_router.router)
api_router.include_router(embeddings_router.router)
api_router.include_router(memory_router.router)
api_router.include_router(knowledge_router.router)
api_router.include_router(documents_router.router)
api_router.include_router(datasets_router.router)
api_router.include_router(evaluations_router.router)
api_router.include_router(experiments_router.router)
api_router.include_router(conversations_router.router)
api_router.include_router(reports_router.router)
api_router.include_router(monitoring_router.router)
api_router.include_router(observability_router.router)
api_router.include_router(notifications_router.router)
api_router.include_router(search_router.router)
api_router.include_router(configuration_router.router)
api_router.include_router(plugins_router.router)
api_router.include_router(audit_logs_router.router)
