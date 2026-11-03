"""Structlog configuration for the AI Core: JSON output in production,
readable console output in development, with correlation ID automatically
attached to every log line."""
from __future__ import annotations

import logging

import structlog

from ai_core.config.settings import AICoreSettings
from ai_core.observability.context import get_correlation_id


def _add_correlation_id(logger, method_name, event_dict):  # noqa: ANN001
    correlation_id = get_correlation_id()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_logging(settings: AICoreSettings | None = None) -> None:
    settings = settings or AICoreSettings()
    logging.basicConfig(level=settings.log_level, format="%(message)s")

    renderer = structlog.processors.JSONRenderer() if settings.log_json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_correlation_id,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "ai_core"):
    return structlog.get_logger(name)
