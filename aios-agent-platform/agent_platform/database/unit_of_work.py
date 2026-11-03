"""Async context manager committing/rolling back one transaction across
every repository in a RepositoryRegistry."""
from __future__ import annotations

from agent_platform.database.session import async_session_factory
from agent_platform.repositories.registry import RepositoryRegistry


class UnitOfWork:
    async def __aenter__(self) -> RepositoryRegistry:
        self._session_ctx = async_session_factory()
        self.session = await self._session_ctx.__aenter__()
        self.repos = RepositoryRegistry(self.session)
        return self.repos

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self._session_ctx.__aexit__(exc_type, exc, tb)
