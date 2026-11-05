"""Generic async repository — manual optimistic locking, soft delete,
pagination. Same pattern as every AIOS service."""
from __future__ import annotations


from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from memory_platform.core.exceptions import ConcurrentModificationError, NotFoundError
from memory_platform.core.pagination import Page, PaginationParams
from memory_platform.database.base import Base
from memory_platform.clock import utc_now

ModelType = TypeVar("ModelType", bound=Base)


class SQLAlchemyRepository(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: str, *, include_deleted: bool = False) -> ModelType | None:
        obj = await self.session.get(self.model, id)
        if obj is None:
            return None
        if not include_deleted and getattr(obj, "is_deleted", False):
            return None
        return obj

    async def get_or_404(self, id: str) -> ModelType:
        obj = await self.get(id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} '{id}' not found")
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
        if expected_version is not None and hasattr(entity, "version"):
            current = await self.session.get(self.model, entity.id)
            if current is not None and current.version != expected_version:
                raise ConcurrentModificationError(
                    f"{self.model.__name__} '{entity.id}' was modified concurrently "
                    f"(expected version {expected_version}, found {current.version})"
                )
            entity.version = expected_version + 1
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelType, *, hard: bool = False) -> None:
        if hard or not hasattr(entity, "is_deleted"):
            await self.session.delete(entity)
        else:
            entity.is_deleted = True
            entity.deleted_at = utc_now()
        await self.session.flush()

    async def list(
        self, *, filters: dict[str, Any] | None = None, include_deleted: bool = False, limit: int = 100, offset: int = 0
    ) -> list[ModelType]:
        stmt = select(self.model)
        if not include_deleted and hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))
        for field, value in (filters or {}).items():
            stmt = stmt.where(getattr(self.model, field) == value)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def paginated_list(
        self, params: PaginationParams, *, filters: dict[str, Any] | None = None, include_deleted: bool = False
    ) -> Page[ModelType]:
        base_stmt = select(self.model)
        if not include_deleted and hasattr(self.model, "is_deleted"):
            base_stmt = base_stmt.where(self.model.is_deleted.is_(False))
        for field, value in (filters or {}).items():
            base_stmt = base_stmt.where(getattr(self.model, field) == value)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        items_stmt = base_stmt.limit(params.page_size).offset(params.offset)
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return Page(items=items, total=total, page=params.page, page_size=params.page_size)
