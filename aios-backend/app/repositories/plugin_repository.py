from app.models.plugin import PluginModel, ToolModel
from app.repositories.base import SQLAlchemyRepository


class PluginRepository(SQLAlchemyRepository[PluginModel]):
    model = PluginModel


class ToolRepository(SQLAlchemyRepository[ToolModel]):
    model = ToolModel
