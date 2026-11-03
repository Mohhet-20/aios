"""Pure-Python domain entities with guarded state machines — no ORM
imports. Each entity mirrors the `status` column on its ORM model;
services translate ORM <-> entity, apply a transition, and persist the
resulting status back. Same pattern as every prior AIOS platform.
Simpler status-only resources (KPI definitions, metric definitions,
report/security policies) are guarded directly in-service instead —
the same precedent set by every prior platform for lightly-stated
resources."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from analytics_platform.core.exceptions import InvalidTransitionError
from analytics_platform.domain.enums import (
    DashboardStatus,
    ExportJobStatus,
    ForecastJobStatus,
    RecommendationStatus,
    ReportRunStatus,
)
from analytics_platform.clock import utc_now


def _now() -> datetime:
    return utc_now()


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# -- ReportRun -------------------------------------------------------------------------------------

_REPORT_RUN_TRANSITIONS: dict[ReportRunStatus, set[ReportRunStatus]] = {
    ReportRunStatus.QUEUED: {ReportRunStatus.GENERATING},
    ReportRunStatus.GENERATING: {ReportRunStatus.COMPLETED, ReportRunStatus.FAILED},
    ReportRunStatus.COMPLETED: set(),
    ReportRunStatus.FAILED: set(),
}


@dataclass
class ReportRun:
    id: str
    status: ReportRunStatus = ReportRunStatus.QUEUED

    def _transition(self, target: ReportRunStatus) -> None:
        allowed = _REPORT_RUN_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ReportRun '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(ReportRunStatus.GENERATING)

    def complete(self) -> None:
        self._transition(ReportRunStatus.COMPLETED)

    def fail(self) -> None:
        self._transition(ReportRunStatus.FAILED)


# -- ForecastJob -------------------------------------------------------------------------------------

_FORECAST_JOB_TRANSITIONS: dict[ForecastJobStatus, set[ForecastJobStatus]] = {
    ForecastJobStatus.QUEUED: {ForecastJobStatus.RUNNING},
    ForecastJobStatus.RUNNING: {ForecastJobStatus.COMPLETED, ForecastJobStatus.FAILED},
    ForecastJobStatus.COMPLETED: set(),
    ForecastJobStatus.FAILED: set(),
}


@dataclass
class ForecastJob:
    id: str
    status: ForecastJobStatus = ForecastJobStatus.QUEUED

    def _transition(self, target: ForecastJobStatus) -> None:
        allowed = _FORECAST_JOB_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"ForecastJob '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(ForecastJobStatus.RUNNING)

    def complete(self) -> None:
        self._transition(ForecastJobStatus.COMPLETED)

    def fail(self) -> None:
        self._transition(ForecastJobStatus.FAILED)


# -- Recommendation -------------------------------------------------------------------------------------

_RECOMMENDATION_TRANSITIONS: dict[RecommendationStatus, set[RecommendationStatus]] = {
    RecommendationStatus.OPEN: {RecommendationStatus.ACCEPTED, RecommendationStatus.DISMISSED},
    RecommendationStatus.ACCEPTED: {RecommendationStatus.IMPLEMENTED, RecommendationStatus.DISMISSED},
    RecommendationStatus.DISMISSED: set(),
    RecommendationStatus.IMPLEMENTED: set(),
}


@dataclass
class Recommendation:
    id: str
    status: RecommendationStatus = RecommendationStatus.OPEN

    def _transition(self, target: RecommendationStatus) -> None:
        allowed = _RECOMMENDATION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Recommendation '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def accept(self) -> None:
        self._transition(RecommendationStatus.ACCEPTED)

    def dismiss(self) -> None:
        self._transition(RecommendationStatus.DISMISSED)

    def implement(self) -> None:
        self._transition(RecommendationStatus.IMPLEMENTED)


# -- Dashboard -------------------------------------------------------------------------------------

_DASHBOARD_TRANSITIONS: dict[DashboardStatus, set[DashboardStatus]] = {
    DashboardStatus.DRAFT: {DashboardStatus.PUBLISHED},
    DashboardStatus.PUBLISHED: {DashboardStatus.ARCHIVED},
    DashboardStatus.ARCHIVED: {DashboardStatus.PUBLISHED},
}


@dataclass
class Dashboard:
    id: str
    status: DashboardStatus = DashboardStatus.DRAFT

    def _transition(self, target: DashboardStatus) -> None:
        allowed = _DASHBOARD_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"Dashboard '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def publish(self) -> None:
        self._transition(DashboardStatus.PUBLISHED)

    def archive(self) -> None:
        self._transition(DashboardStatus.ARCHIVED)

    def republish(self) -> None:
        self._transition(DashboardStatus.PUBLISHED)


# -- DataExportJob -------------------------------------------------------------------------------------

_EXPORT_JOB_TRANSITIONS: dict[ExportJobStatus, set[ExportJobStatus]] = {
    ExportJobStatus.QUEUED: {ExportJobStatus.RUNNING},
    ExportJobStatus.RUNNING: {ExportJobStatus.COMPLETED, ExportJobStatus.FAILED},
    ExportJobStatus.COMPLETED: set(),
    ExportJobStatus.FAILED: set(),
}


@dataclass
class DataExportJob:
    id: str
    status: ExportJobStatus = ExportJobStatus.QUEUED

    def _transition(self, target: ExportJobStatus) -> None:
        allowed = _EXPORT_JOB_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidTransitionError(f"DataExportJob '{self.id}' cannot transition from {self.status.value} to {target.value}")
        self.status = target

    def start(self) -> None:
        self._transition(ExportJobStatus.RUNNING)

    def complete(self) -> None:
        self._transition(ExportJobStatus.COMPLETED)

    def fail(self) -> None:
        self._transition(ExportJobStatus.FAILED)
