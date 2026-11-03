from app.models.knowledge import DocumentModel, KnowledgeCollectionModel
from app.repositories.base import SQLAlchemyRepository


class KnowledgeCollectionRepository(SQLAlchemyRepository[KnowledgeCollectionModel]):
    model = KnowledgeCollectionModel


class DocumentRepository(SQLAlchemyRepository[DocumentModel]):
    model = DocumentModel
