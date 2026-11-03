"""KnowledgeService — the centralized Knowledge Platform: knowledge
bases -> collections -> items, each item going through a real
draft/review/publish workflow (`KnowledgeItem` domain entity) with an
append-only version history, ownership, categories/tags, validation
before publish, and relationship linking against the shared Knowledge
Graph substrate (`KGEntityModel`/`KGRelationshipModel`) rather than a
second, redundant relationship model.
"""
from __future__ import annotations

from datetime import datetime

from memory_platform.core.exceptions import ValidationError
from memory_platform.database.base import new_uuid
from memory_platform.domain.entities import KnowledgeItem
from memory_platform.domain.enums import KnowledgeItemStatus, WellKnownRelationType
from memory_platform.models.knowledge import (
    KnowledgeBaseModel,
    KnowledgeCollectionModel,
    KnowledgeItemModel,
    KnowledgeItemVersionModel,
)
from memory_platform.models.knowledge_graph import KGEntityModel, KGRelationshipModel
from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _item_to_domain(model: KnowledgeItemModel) -> KnowledgeItem:
    return KnowledgeItem(
        id=model.id, workspace_id=model.workspace_id, knowledge_base_id=model.knowledge_base_id,
        title=model.title, content=model.content, owner_id=model.owner_id, collection_id=model.collection_id,
        summary=model.summary, category=model.category, tags=list(model.tags or []),
        status=KnowledgeItemStatus(model.status), version=model.version, reviewed_by=model.reviewed_by,
    )


def _apply_item_to_model(entity: KnowledgeItem, model: KnowledgeItemModel) -> KnowledgeItemModel:
    model.title = entity.title
    model.content = entity.content
    model.summary = entity.summary
    model.category = entity.category
    model.tags = list(entity.tags or [])
    model.status = entity.status.value
    model.version = entity.version
    model.reviewed_by = entity.reviewed_by
    model.collection_id = entity.collection_id
    return model


class KnowledgeService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- knowledge base / collection ------------------------------------------------

    async def create_knowledge_base(self, *, workspace_id: str, name: str, slug: str, owner_id: str, description: str | None = None) -> KnowledgeBaseModel:
        return await self.repos.knowledge_bases.add(KnowledgeBaseModel(
            id=new_uuid(), workspace_id=workspace_id, name=name, slug=slug, description=description, owner_id=owner_id,
        ))

    async def create_collection(self, *, knowledge_base_id: str, name: str, slug: str, parent_collection_id: str | None = None, description: str | None = None) -> KnowledgeCollectionModel:
        return await self.repos.knowledge_collections.add(KnowledgeCollectionModel(
            id=new_uuid(), knowledge_base_id=knowledge_base_id, parent_collection_id=parent_collection_id, name=name, slug=slug, description=description,
        ))

    async def list_collections(self, knowledge_base_id: str) -> list[KnowledgeCollectionModel]:
        return await self.repos.knowledge_collections.list_by_knowledge_base(knowledge_base_id)

    # -- item creation / validation --------------------------------------------------

    @staticmethod
    def validate_item(*, title: str, content: str) -> None:
        if not title or not title.strip():
            raise ValidationError("knowledge item title must not be empty")
        if not content or not content.strip():
            raise ValidationError("knowledge item content must not be empty")

    async def create_item(
        self, *, workspace_id: str, knowledge_base_id: str, title: str, content: str, owner_id: str,
        collection_id: str | None = None, category: str | None = None, tags: list | None = None,
        source_document_id: str | None = None, summary: str | None = None,
    ) -> KnowledgeItemModel:
        self.validate_item(title=title, content=content)
        model = KnowledgeItemModel(
            id=new_uuid(), workspace_id=workspace_id, knowledge_base_id=knowledge_base_id, collection_id=collection_id,
            source_document_id=source_document_id, title=title, content=content, summary=summary, category=category,
            tags=tags or [], owner_id=owner_id, status=KnowledgeItemStatus.DRAFT.value,
        )
        created = await self.repos.knowledge_items.add(model)
        await self._record_version(created, changed_by=owner_id, change_note="initial draft")
        return created

    async def _record_version(self, model: KnowledgeItemModel, *, changed_by: str, change_note: str | None) -> KnowledgeItemVersionModel:
        return await self.repos.knowledge_item_versions.add(KnowledgeItemVersionModel(
            id=new_uuid(), knowledge_item_id=model.id, version_number=model.version, content=model.content,
            summary=model.summary, changed_by=changed_by, change_note=change_note,
        ))

    async def update_content(self, item_id: str, *, content: str, changed_by: str, summary: str | None = None, change_note: str | None = None) -> KnowledgeItemModel:
        if not content or not content.strip():
            raise ValidationError("knowledge item content must not be empty")
        model = await self.repos.knowledge_items.get_or_404(item_id)
        entity = _item_to_domain(model)
        entity.new_version(content, summary=summary)
        _apply_item_to_model(entity, model)
        await self.repos.knowledge_items.update(model)
        await self._record_version(model, changed_by=changed_by, change_note=change_note)
        return model

    # -- review / publish workflow ----------------------------------------------------

    async def submit_for_review(self, item_id: str) -> KnowledgeItemModel:
        return await self._transition(item_id, "submit_for_review")

    async def approve_and_publish(self, item_id: str, *, reviewed_by: str) -> KnowledgeItemModel:
        model = await self.repos.knowledge_items.get_or_404(item_id)
        entity = _item_to_domain(model)
        entity.approve_and_publish(reviewed_by)
        _apply_item_to_model(entity, model)
        model.reviewed_at = _now()
        model.published_at = _now()
        await self.repos.knowledge_items.update(model)
        await self._ensure_kg_entity(model)
        return model

    async def reject(self, item_id: str, *, reviewed_by: str) -> KnowledgeItemModel:
        model = await self.repos.knowledge_items.get_or_404(item_id)
        entity = _item_to_domain(model)
        entity.reject(reviewed_by)
        _apply_item_to_model(entity, model)
        model.reviewed_at = _now()
        await self.repos.knowledge_items.update(model)
        return model

    async def deprecate(self, item_id: str) -> KnowledgeItemModel:
        return await self._transition(item_id, "deprecate")

    async def archive(self, item_id: str) -> KnowledgeItemModel:
        return await self._transition(item_id, "archive")

    async def _transition(self, item_id: str, action: str) -> KnowledgeItemModel:
        model = await self.repos.knowledge_items.get_or_404(item_id)
        entity = _item_to_domain(model)
        getattr(entity, action)()
        _apply_item_to_model(entity, model)
        await self.repos.knowledge_items.update(model)
        return model

    # -- retrieval -------------------------------------------------------------------

    async def get(self, item_id: str) -> KnowledgeItemModel:
        return await self.repos.knowledge_items.get_or_404(item_id)

    async def list_versions(self, item_id: str) -> list[KnowledgeItemVersionModel]:
        return await self.repos.knowledge_item_versions.list_for_item(item_id)

    async def search(self, workspace_id: str, query: str, *, status: str | None = None, limit: int = 50) -> list[KnowledgeItemModel]:
        return await self.repos.knowledge_items.search(workspace_id, query, status=status, limit=limit)

    async def list_by_knowledge_base(self, knowledge_base_id: str, *, status: str | None = None) -> list[KnowledgeItemModel]:
        return await self.repos.knowledge_items.list_by_knowledge_base(knowledge_base_id, status=status)

    # -- knowledge relationships (backed by the shared Knowledge Graph substrate) ----

    async def _ensure_kg_entity(self, model: KnowledgeItemModel) -> KGEntityModel:
        existing = await self.repos.kg_entities.get_by_ref(model.workspace_id, "knowledge_item", model.id)
        if existing is not None:
            return existing
        return await self.repos.kg_entities.add(KGEntityModel(
            id=new_uuid(), workspace_id=model.workspace_id, entity_type="knowledge_item", name=model.title,
            ref_id=model.id, entity_metadata={"category": model.category, "tags": model.tags},
        ))

    async def link_related(self, item_id: str, related_item_id: str, *, relation_type: str = WellKnownRelationType.RELATED_TO.value, weight: float = 1.0) -> KGRelationshipModel:
        source = await self.repos.knowledge_items.get_or_404(item_id)
        target = await self.repos.knowledge_items.get_or_404(related_item_id)
        source_entity = await self._ensure_kg_entity(source)
        target_entity = await self._ensure_kg_entity(target)
        return await self.repos.kg_relationships.add(KGRelationshipModel(
            id=new_uuid(), workspace_id=source.workspace_id, source_entity_id=source_entity.id, target_entity_id=target_entity.id,
            relation_type=relation_type, weight=weight,
        ))

    async def list_related(self, item_id: str) -> list[KGRelationshipModel]:
        entity = await self.repos.kg_entities.get_by_ref((await self.repos.knowledge_items.get_or_404(item_id)).workspace_id, "knowledge_item", item_id)
        if entity is None:
            return []
        return await self.repos.kg_relationships.list_touching(entity.id)
