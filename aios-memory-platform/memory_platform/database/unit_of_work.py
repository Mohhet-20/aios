"""UnitOfWork: async context manager committing/rolling back one
transaction across every repository in a `RepositoryRegistry`."""
from __future__ import annotations

from memory_platform.database.session import async_session_factory
from memory_platform.repositories.registry import RepositoryRegistry


class UnitOfWork:
    async def __aenter__(self) -> RepositoryRegistry:
        self._session = async_session_factory()
        self.repos = RepositoryRegistry(self._session)
        return self.repos

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()
