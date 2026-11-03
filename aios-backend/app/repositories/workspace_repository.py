from app.models.workspace import ProjectModel, WorkspaceModel
from app.repositories.base import SQLAlchemyRepository


class WorkspaceRepository(SQLAlchemyRepository[WorkspaceModel]):
    model = WorkspaceModel


class ProjectRepository(SQLAlchemyRepository[ProjectModel]):
    model = ProjectModel
