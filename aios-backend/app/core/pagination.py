"""Shared pagination / filtering / sorting primitives used by every list
endpoint. One implementation here means every router gets identical
pagination semantics (page/limit, total count, next/prev hints) instead of
each router inventing its own query-param contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, asc, desc, func, select

T = TypeVar("T")
SortDir = Literal["asc", "desc"]


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: int = Query(1, ge=1, description="1-indexed page number"),
    page_size: int = Query(20, ge=1, le=200, description="Items per page (max 200)"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


@dataclass
class SortParams:
    field: str | None
    direction: SortDir = "desc"


def sort_params(
    sort_by: str | None = Query(None, description="Column to sort by"),
    sort_dir: SortDir = Query("desc", description="Sort direction"),
) -> SortParams:
    return SortParams(field=sort_by, direction=sort_dir)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def create(cls, items: list[T], total: int, params: PaginationParams) -> Page[T]:
        total_pages = max(1, -(-total // params.page_size))  # ceil div
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )


async def paginate(
    session,
    base_query: Select,
    count_query: Select,
    params: PaginationParams,
    sort: SortParams | None = None,
    sortable_columns: dict[str, InstrumentedAttribute] | None = None,  # noqa: F821
) -> tuple[list, int]:
    """Apply sort + limit/offset to `base_query`, run both it and
    `count_query`, and return (rows, total). Kept as a free function (not a
    repository method) so it can be reused across repositories without
    inheritance gymnastics.
    """
    if sort and sort.field and sortable_columns and sort.field in sortable_columns:
        column = sortable_columns[sort.field]
        base_query = base_query.order_by(desc(column) if sort.direction == "desc" else asc(column))

    base_query = base_query.offset(params.offset).limit(params.page_size)

    result = await session.execute(base_query)
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()
    return list(result.scalars().unique().all()), total


def count_query_for(model) -> Select:
    return select(func.count()).select_from(model)
