"""Shared AI Core wiring. Semantic tool-discovery search / embedding-backed
capability matching take an `AICoreContext` through their constructor
rather than importing a singleton directly — exactly like the Workflow
Engine — so tests can inject a scripted, network-free context."""
from __future__ import annotations

from functools import lru_cache

from ai_core.bootstrap import AICoreContext, build_ai_core


@lru_cache
def get_default_ai_core_context() -> AICoreContext:
    """Process-wide default context for production use. Tests build their
    own `AICoreContext` from scripted providers and pass it explicitly."""
    return build_ai_core()
