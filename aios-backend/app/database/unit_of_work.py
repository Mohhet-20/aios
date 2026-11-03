"""Unit of Work: groups one or more repository operations into a single
transaction so a use case that touches multiple aggregates (e.g. "promote a
prompt version AND write an audit log entry AND emit a domain event") either
commits atomically or rolls back atomically — never half-applied.

Services receive a `UnitOfWork` (via DI) rather than a raw session so they
never call `session.commit()` themselves; only the boundary that opened the
unit of work does, which keeps transaction scope aligned with use-case scope
instead of leaking into every repository call.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import async_session_factory
from app.repositories.registry import RepositoryRegistry


class UnitOfWork:
    def __init__(self) -> None:
        self._session: AsyncSession | None = None
        self.repos: RepositoryRegistry | None = None

    async def __aenter__(self) -> UnitOfWork:
        self._session = async_session_factory()
        self.repos = RepositoryRegistry(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        assert self._session is not None, "UnitOfWork not entered — use 'async with UnitOfWork() as uow:'"
        return self._session
