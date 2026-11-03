from __future__ import annotations

from fastapi import Request

from ai_core.bootstrap import AICoreContext


def get_context(request: Request) -> AICoreContext:
    return request.app.state.ai_core
