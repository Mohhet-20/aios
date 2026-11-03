"""ChecklistService: simple ordered checklists attached to a task or
an asset."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ValidationError
from collaboration_platform.models.productivity import ChecklistItemModel, ChecklistModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class ChecklistService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_checklist(
        self, *, title: str, created_by: str, task_id: str | None = None, asset_id: str | None = None
    ) -> ChecklistModel:
        if task_id is None and asset_id is None:
            raise ValidationError("a checklist must belong to either a task or an asset")
        return await self.repos.checklists.add(ChecklistModel(task_id=task_id, asset_id=asset_id, title=title, created_by=created_by))

    async def add_item(self, checklist_id: str, *, text: str, position: int | None = None) -> ChecklistItemModel:
        await self.repos.checklists.get_or_404(checklist_id)
        if position is None:
            existing = await self.repos.checklist_items.list_for_checklist(checklist_id)
            position = len(existing)
        return await self.repos.checklist_items.add(ChecklistItemModel(checklist_id=checklist_id, text=text, position=position))

    async def toggle_item(self, item_id: str) -> ChecklistItemModel:
        item = await self.repos.checklist_items.get_or_404(item_id)
        item.is_done = not item.is_done
        return await self.repos.checklist_items.update(item)

    async def list_items(self, checklist_id: str) -> list[ChecklistItemModel]:
        return await self.repos.checklist_items.list_for_checklist(checklist_id)

    async def list_for_task(self, task_id: str) -> list[ChecklistModel]:
        return await self.repos.checklists.list_for_task(task_id)

    async def list_for_asset(self, asset_id: str) -> list[ChecklistModel]:
        return await self.repos.checklists.list_for_asset(asset_id)
