"""Thin re-export so routers/services import DB dependencies from
`app.dependencies` (the conventional FastAPI DI location) rather than
reaching into `app.database` directly — keeps the import surface
consistent with `auth_dependencies` and `service_dependencies`.
"""

from app.database.session import get_db_session
from app.database.unit_of_work import UnitOfWork

__all__ = ["get_db_session", "UnitOfWork", "get_unit_of_work"]


async def get_unit_of_work():
    async with UnitOfWork() as uow:
        yield uow
        await uow.commit()
