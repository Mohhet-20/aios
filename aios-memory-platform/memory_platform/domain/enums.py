"""Every enum in the platform. `MemoryType` is deliberately data enough to
double as a lookup key into `MemoryTypePolicyModel` (the data-driven
policy table) rather than a hardcoded switch statement anywhere in the
service layer — new memory *behavior* is a new policy row, new memory
*kinds that need bespoke code* (conversation/episodic/working) get their
own thin service on top of the same MemoryEntryModel table.
"""
from __future__ import annotations

from enum import Enum


class MemoryType(str, Enum):
    WORKING = "working"
    CONVERSATION = "conversation"
    SESSION = "session"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    SHARED_TEAM = "shared_team"
    ORGANIZATIONAL = "organizational"
    PROJECT = "project"
    USER = "user"
    AGENT = "agent"
    WORKFLOW = "workflow"
    EXECUTION = "execution"
    KNOWLEDGE = "knowledge"


class ScopeType(str, Enum):
    """Who a memory entry belongs to — orthogonal to `MemoryType` (its
    cognitive category). An EPISODIC memory can be scoped to a USER or to
    an AGENT; scope answers "whose," type answers "what kind."""

    USER = "user"
    AGENT = "agent"
    SESSION = "session"
    PROJECT = "project"
    TEAM = "team"
    ORGANIZATION = "organization"
    WORKFLOW = "workflow"
    EXECUTION = "execution"
    GLOBAL = "global"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class KnowledgeItemStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    WEBPAGE = "webpage"


class SearchMode(str, Enum):
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RetentionAction(str, Enum):
    ARCHIVE = "archive"
    DELETE = "delete"
    SUMMARIZE = "summarize"


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_PUBLISH = "knowledge:publish"
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_PROCESS = "document:process"
    GRAPH_READ = "graph:read"
    GRAPH_WRITE = "graph:write"
    RETRIEVAL_QUERY = "retrieval:query"
    AUDIT_READ = "audit:read"
    WORKSPACE_MANAGE = "workspace:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset({
        Permission.MEMORY_READ, Permission.MEMORY_WRITE, Permission.MEMORY_DELETE,
        Permission.KNOWLEDGE_READ, Permission.KNOWLEDGE_WRITE, Permission.KNOWLEDGE_PUBLISH,
        Permission.DOCUMENT_UPLOAD, Permission.DOCUMENT_PROCESS, Permission.GRAPH_READ, Permission.GRAPH_WRITE,
        Permission.RETRIEVAL_QUERY, Permission.AUDIT_READ,
    }),
    Role.OPERATOR: frozenset({
        Permission.MEMORY_READ, Permission.MEMORY_WRITE, Permission.KNOWLEDGE_READ, Permission.KNOWLEDGE_WRITE,
        Permission.DOCUMENT_UPLOAD, Permission.DOCUMENT_PROCESS, Permission.GRAPH_READ, Permission.RETRIEVAL_QUERY,
    }),
    Role.VIEWER: frozenset({Permission.MEMORY_READ, Permission.KNOWLEDGE_READ, Permission.GRAPH_READ, Permission.RETRIEVAL_QUERY}),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


# Well-known knowledge-graph relationship types — a documented vocabulary,
# not a closed enum, since real knowledge graphs need arbitrary relation
# types (`KGRelationshipModel.relation_type` is a plain string column).
class WellKnownRelationType(str, Enum):
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    DEPENDS_ON = "depends_on"
    MENTIONS = "mentions"
    AUTHORED_BY = "authored_by"
    DERIVED_FROM = "derived_from"
    SIMILAR_TO = "similar_to"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    OWNS = "owns"
