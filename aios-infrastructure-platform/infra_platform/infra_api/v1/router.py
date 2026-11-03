"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from infra_platform.infra_api.v1 import (
    artifacts,
    autoscaling,
    cicd,
    cloud,
    containers,
    deployment,
    experiments,
    feature_store,
    inference,
    kubernetes,
    model_registry,
    observability,
    recovery,
    security,
)

api_router = APIRouter()
api_router.include_router(containers.router)
api_router.include_router(kubernetes.router)
api_router.include_router(cicd.router)
api_router.include_router(model_registry.router)
api_router.include_router(experiments.router)
api_router.include_router(feature_store.router)
api_router.include_router(artifacts.router)
api_router.include_router(inference.router)
api_router.include_router(deployment.router)
api_router.include_router(autoscaling.router)
api_router.include_router(cloud.router)
api_router.include_router(recovery.router)
api_router.include_router(observability.router)
api_router.include_router(security.router)
