"""Generic async SQLAlchemy repository.

Implements `AbstractRepository` once; every entity-specific repository in
this package subclasses `SQLAlchemyRepository[ModelType]` and only adds
methods for queries the generic implementation can't express (see
`app.repositories.prompt_repository` for an example). This is what lets 20+
services share one persistence implementation instead of hand-rolling CRUD
20+ times.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import utc_now
from app.core.exceptions import ConcurrentModificationError, NotFoundError
from app.core.pagination import PaginationParams, SortParams, count_query_for, paginate
from app.database.base import SoftDeleteMixin, VersionedMixin

ModelType = TypeVar("ModelType")


class SQLAlchemyRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    def _base_query(self, include_deleted: bool = False):
        query = select(self.model)
        if issubclass(self.model, SoftDeleteMixin) and not include_deleted:
            query = query.where(self.model.is_deleted.is_(False))  # type: ignore[attr-defined]
        return query

    async def get(self, id: str, *, include_deleted: bool = False) -> ModelType | None:
        query = self._base_query(include_deleted).where(self.model.id == id)  # type: ignore[attr-defined]
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_or_404(self, id: str) -> ModelType:
        obj = await self.get(id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} with id '{id}' was not found")
        return obj

    async def get_many(self, ids: list[str], *, include_deleted: bool = False) -> list[ModelType]:
        """Batch-fetch by primary key in a single query — replaces the
        N+1 "loop calling await repo.get(id) per item" pattern (see the
        performance audit). Preserves the input order and
        silently skips ids with no matching row, matching the behavior
        of the loops it replaces."""
        if not ids:
            return []
        stmt = select(self.model).where(self.model.id.in_(ids))
        if not include_deleted and hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        by_id = {obj.id: obj for obj in result.scalars().all()}
        return [by_id[i] for i in ids if i in by_id]

    async def add(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: ModelType, *, expected_version: int | None = None) -> ModelType:
        if expected_version is not None and issubclass(self.model, VersionedMixin):
            current = await self.get(entity.id)  # type: ignore[attr-defined]
            if current is None:
                raise NotFoundError(f"{self.model.__name__} with id '{entity.id}' was not found")  # type: ignore[attr-defined]
            if current.version != expected_version:  # type: ignore[attr-defined]
                raise ConcurrentModificationError(
                    f"{self.model.__name__} was modified by another request",
                    expected_version=expected_version,
                    actual_version=current.version,  # type: ignore[attr-defined]
                )
            entity.version = expected_version + 1  # type: ignore[attr-defined]
        await self.session.flush()
        return entity

    async def delete(self, id: str, *, soft: bool = True) -> None:
        entity = await self.get_or_404(id)
        if soft and isinstance(entity, SoftDeleteMixin):
            entity.is_deleted = True
            entity.deleted_at = utc_now()
            await self.session.flush()
        else:
            await self.session.delete(entity)
            await self.session.flush()

    async def list(self, **filters) -> list[ModelType]:
        query = self._base_query()
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def paginated_list(
        self,
        params: PaginationParams,
        sort: SortParams | None = None,
        sortable_columns: dict | None = None,
        **filters,
    ) -> tuple[list[ModelType], int]:
        query = self._base_query()
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)
        count_q = count_query_for(self.model)
        for field, value in filters.items():
            if value is not None:
                count_q = count_q.where(getattr(self.model, field) == value)
        return await paginate(self.session, query, count_q, params, sort, sortable_columns)
