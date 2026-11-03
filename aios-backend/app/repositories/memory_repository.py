from app.models.memory import MemoryItemModel
from app.repositories.base import SQLAlchemyRepository


class MemoryRepository(SQLAlchemyRepository[MemoryItemModel]):
    model = MemoryItemModel

    async def list_by_type(self, workspace_id: str, memory_type: str | None = None) -> list[MemoryItemModel]:
        filters = {"workspace_id": workspace_id}
        if memory_type:
            filters["memory_type"] = memory_type
        return await self.list(**filters)
