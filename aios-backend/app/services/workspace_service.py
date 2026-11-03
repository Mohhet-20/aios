from app.application.services.base_service import BaseCRUDService
from app.models.workspace import ProjectModel, WorkspaceModel
from app.repositories.workspace_repository import ProjectRepository, WorkspaceRepository


class WorkspaceService(BaseCRUDService[WorkspaceModel]):
    def __init__(self, repository: WorkspaceRepository):
        super().__init__(repository)


class ProjectService(BaseCRUDService[ProjectModel]):
    def __init__(self, repository: ProjectRepository):
        super().__init__(repository)

    async def update_progress(self, project_id: str, progress: int) -> ProjectModel:
        project = await self.repository.get_or_404(project_id)
        project.progress = max(0, min(100, progress))
        return await self.repository.update(project)
