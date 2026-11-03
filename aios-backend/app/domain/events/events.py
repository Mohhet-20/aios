"""Concrete domain/application/workflow/AI/notification/audit/plugin events.

Grouped by the categories the Phase 1 blueprint calls out (Domain, Workflow,
AI, Notification, Audit, Plugin events) even though they share one base
class — the categorization is about *intent* (who subscribes to what), not
a different mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.events.base import DomainEvent


# --- Identity / domain events ---
@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    user_id: str
    email: str


@dataclass(frozen=True, kw_only=True)
class UserLoggedIn(DomainEvent):
    user_id: str


# --- Agent / prompt domain events ---
@dataclass(frozen=True, kw_only=True)
class AgentCreated(DomainEvent):
    agent_id: str
    name: str


@dataclass(frozen=True, kw_only=True)
class PromptVersionCreated(DomainEvent):
    prompt_id: str
    version: int


@dataclass(frozen=True, kw_only=True)
class PromptPromoted(DomainEvent):
    prompt_id: str
    version: int
    to_status: str


# --- Workflow events ---
@dataclass(frozen=True, kw_only=True)
class WorkflowExecutionStarted(DomainEvent):
    execution_id: str
    workflow_id: str


@dataclass(frozen=True, kw_only=True)
class WorkflowExecutionCompleted(DomainEvent):
    execution_id: str
    workflow_id: str
    success: bool


# --- AI events ---
@dataclass(frozen=True, kw_only=True)
class InferenceRequested(DomainEvent):
    request_id: str
    model_id: str


@dataclass(frozen=True, kw_only=True)
class InferenceCompleted(DomainEvent):
    request_id: str
    model_id: str
    latency_ms: float
    token_count: int


@dataclass(frozen=True, kw_only=True)
class EvaluationCompleted(DomainEvent):
    evaluation_run_id: str
    score: float
    passed: int
    failed: int


# --- Notification events ---
@dataclass(frozen=True, kw_only=True)
class NotificationCreated(DomainEvent):
    notification_id: str
    recipient_user_id: str


# --- Audit events ---
@dataclass(frozen=True, kw_only=True)
class AuditableActionPerformed(DomainEvent):
    action: str
    resource: str
    status: str


# --- Plugin events ---
@dataclass(frozen=True, kw_only=True)
class PluginInstalled(DomainEvent):
    plugin_id: str
    name: str


@dataclass(frozen=True, kw_only=True)
class PluginToggled(DomainEvent):
    plugin_id: str
    enabled: bool
