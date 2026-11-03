"""Request-scoped correlation context, propagated via contextvars so any log
statement anywhere in the call stack (service, repository, worker job) can
tag itself with the request/correlation ID without threading it through
every function signature."""

from contextvars import ContextVar
from uuid import uuid4

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")


def new_request_id() -> str:
    return uuid4().hex


def get_request_id() -> str:
    return request_id_ctx.get()


def get_correlation_id() -> str:
    return correlation_id_ctx.get() or get_request_id()


def set_context(request_id: str, correlation_id: str | None = None, user_id: str | None = None) -> None:
    request_id_ctx.set(request_id)
    correlation_id_ctx.set(correlation_id or request_id)
    if user_id:
        user_id_ctx.set(user_id)
