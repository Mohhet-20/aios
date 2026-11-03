"""Generic CRUD application service.

Every "lighter" business service (ProjectService, WorkspaceService,
KnowledgeService, DatasetService, ...) subclasses this instead of
reimplementing get/list/create/update/delete — the same leverage
`SQLAlchemyRepository` gives the persistence layer, one level up. Services
that need real domain rules (PromptService, WorkflowService, AgentService,
AuthService, EvaluationService) override or extend these methods with
actual business logic rather than being pure passthroughs.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from app.core.pagination import Page, PaginationParams, SortParams
from app.repositories.base import SQLAlchemyRepository

ModelType = TypeVar("ModelType")


class BaseCRUDService(Generic[ModelType]):
    def __init__(self, repository: SQLAlchemyRepository[ModelType]):
        self.repository = repository

    async def get(self, id: str) -> ModelType:
        return await self.repository.get_or_404(id)

    async def list(self, **filters) -> list[ModelType]:
        return await self.repository.list(**filters)

    async def list_paginated(
        self,
        params: PaginationParams,
        sort: SortParams | None = None,
        sortable_columns: dict | None = None,
        **filters,
    ) -> Page[ModelType]:
        items, total = await self.repository.paginated_list(params, sort, sortable_columns, **filters)
        return Page.create(items, total, params)

    async def create(self, entity: ModelType) -> ModelType:
        return await self.repository.add(entity)

    async def update(self, entity: ModelType, *, expected_version: int | None = None) -> ModelType:
        return await self.repository.update(entity, expected_version=expected_version)

    async def delete(self, id: str, *, soft: bool = True) -> None:
        await self.repository.delete(id, soft=soft)
