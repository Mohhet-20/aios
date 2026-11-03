"""Structlog configuration — same pattern used across the AIOS backend and
AI Core, kept self-contained here since this is an independently
deployable service."""
from __future__ import annotations

import logging

import structlog

from prompt_platform.config.settings import Settings


def configure_logging(settings: Settings | None = None) -> None:
    from prompt_platform.config.settings import get_settings

    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(message)s")
    renderer = structlog.processors.JSONRenderer() if settings.log_json else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "prompt_platform"):
    return structlog.get_logger(name)
