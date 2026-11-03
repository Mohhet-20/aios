"""UnitOfWork: async context manager pairing one AsyncSession with one
RepositoryRegistry, committing on clean exit and rolling back on any
exception. Same pattern as every prior AIOS platform's UoW."""
from __future__ import annotations

from types import TracebackType

from workflow_platform.database.session import async_session_factory
from workflow_platform.repositories.registry import RepositoryRegistry


class UnitOfWork:
    def __init__(self) -> None:
        self._session = None
        self.repos: RepositoryRegistry | None = None

    async def __aenter__(self) -> "UnitOfWork":
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
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()

    async def flush(self) -> None:
        assert self._session is not None
        await self._session.flush()
