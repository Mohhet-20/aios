"""Async Unit of Work — one session, one transaction, every repository."""
from __future__ import annotations

from prompt_platform.database.session import async_session_factory
from prompt_platform.repositories.registry import RepositoryRegistry


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


async def get_unit_of_work() -> UnitOfWork:
    return UnitOfWork()
