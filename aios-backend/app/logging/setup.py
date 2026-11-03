"""Structured logging configuration built on `structlog`, layered on top of
stdlib `logging` so third-party libraries (uvicorn, sqlalchemy) still emit
through the same pipeline. Every log line is JSON in production (machine-
parseable by the log aggregator) and colorized key=value in development.

This is the Observability engine's "Structured Logging" requirement made
concrete — every log event automatically carries request_id/correlation_id/
user_id from `app.logging.context` without each call site passing them in.
"""

import logging
import sys

import structlog

from app.logging.context import get_correlation_id, get_request_id, user_id_ctx


def _add_correlation_ids(logger, method_name, event_dict):
    event_dict["request_id"] = get_request_id()
    event_dict["correlation_id"] = get_correlation_id()
    uid = user_id_ctx.get()
    if uid:
        event_dict["user_id"] = uid
    return event_dict


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_correlation_ids,
        structlog.processors.StackInfoRenderer(),
    ]

    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "aios"):
    return structlog.get_logger(name)
