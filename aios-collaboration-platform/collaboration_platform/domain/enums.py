"""Every enum used across the Collaboration Platform's domain, models,
and services in one place — the same convention as every sibling AIOS
platform."""
from __future__ import annotations

from enum import Enum


class WorkspaceType(str, Enum):
    PERSONAL = "personal"
    TEAM = "team"
    ORGANIZATION = "organization"


class WorkspaceStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AssetType(str, Enum):
    PROMPT = "prompt"
    AGENT = "agent"
    WORKFLOW = "workflow"
    KNOWLEDGE_BASE = "knowledge_base"
    DOCUMENT = "document"
    DATASET = "dataset"
    MODEL = "model"
    TOOL = "tool"
    DASHBOARD = "dashboard"
    REPORT = "report"
    TEMPLATE = "template"
    PROJECT = "project"
    CUSTOM = "custom"


class AssetStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class AssetVisibility(str, Enum):
    PRIVATE = "private"
    WORKSPACE = "workspace"
    ORGANIZATION = "organization"
    PUBLIC = "public"


class PresenceStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTED = "disconnected"


class ConflictResolutionStrategy(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    REJECTED = "rejected"


class CommentTargetKind(str, Enum):
    ASSET = "asset"
    VERSION = "version"


class NotificationType(str, Enum):
    MENTION = "mention"
    COMMENT_REPLY = "comment_reply"
    ASSIGNMENT = "assignment"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_DECISION = "approval_decision"
    WORKFLOW_STATUS = "workflow_status"
    AGENT_STATUS = "agent_status"
    PROJECT_UPDATE = "project_update"
    ASSET_SHARED = "asset_shared"
    DIGEST = "digest"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    DIGEST = "digest"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class BranchStatus(str, Enum):
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"


class MergeStrategy(str, Enum):
    FAST_FORWARD = "fast_forward"
    THREE_WAY = "three_way"
    MANUAL = "manual"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReviewAssignmentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"


class LibraryVisibility(str, Enum):
    PRIVATE = "private"
    ORGANIZATION = "organization"
    PUBLIC = "public"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class WorkspaceRole(str, Enum):
    """Coarse workspace-level permission role — deliberately a small,
    ordered set (each implies everything before it) rather than a
    freeform permission-string system, since workspace access control
    only needs to answer "can this principal view / comment / edit /
    administer this workspace", not arbitrary resource-type grants
    (that finer-grained job belongs to the Identity Platform's RBAC)."""
    VIEWER = "viewer"
    COMMENTER = "commenter"
    EDITOR = "editor"
    ADMIN = "admin"
    OWNER = "owner"


class PrincipalType(str, Enum):
    USER = "user"
    TEAM = "team"


class SharePermission(str, Enum):
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"


class ActivityEventType(str, Enum):
    ASSET_CREATED = "asset_created"
    ASSET_UPDATED = "asset_updated"
    ASSET_ARCHIVED = "asset_archived"
    ASSET_DELETED = "asset_deleted"
    VERSION_CREATED = "version_created"
    VERSION_ROLLED_BACK = "version_rolled_back"
    BRANCH_CREATED = "branch_created"
    BRANCH_MERGED = "branch_merged"
    COMMENT_ADDED = "comment_added"
    COMMENT_RESOLVED = "comment_resolved"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"
    WORKSPACE_CREATED = "workspace_created"
    PROJECT_CREATED = "project_created"
    ASSET_SHARED = "asset_shared"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
