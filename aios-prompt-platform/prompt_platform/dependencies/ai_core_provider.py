"""Shared AI Core wiring. Every service that needs to render/execute a
prompt (Studio, Testing, Evaluation, Optimization, Experiments) takes an
`AICoreContext` through its constructor rather than importing a singleton
directly — that's what lets tests inject a context built from scripted
providers instead of the real one, with zero network access.
"""
from __future__ import annotations

from functools import lru_cache

from ai_core.bootstrap import AICoreContext, build_ai_core


@lru_cache
def get_default_ai_core_context() -> AICoreContext:
    """Process-wide default context for production use. Tests should
    build their own `AICoreContext` (see tests/conftest.py) and pass it
    explicitly instead of relying on this cached singleton."""
    return build_ai_core()
