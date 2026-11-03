"""Aggregates every v1 router into one include-able APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from memory_platform.memory_api.v1 import (
    context,
    documents,
    governance,
    knowledge,
    knowledge_graph,
    memory,
    observability,
    retrieval,
    vectors,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(workspaces.router)
api_router.include_router(memory.router)
api_router.include_router(knowledge.router)
api_router.include_router(documents.router)
api_router.include_router(vectors.router)
api_router.include_router(retrieval.router)
api_router.include_router(knowledge_graph.router)
api_router.include_router(context.router)
api_router.include_router(governance.router)
api_router.include_router(observability.router)
