"""Import every ORM model module so `Base.metadata` is fully populated
before `init_models()`/Alembic autogenerate inspects it. This is the one
file in `app/models/` allowed to know that all these tables exist together;
individual model modules stay independent of each other.
"""

from app.models import (  # noqa: F401
    agent,
    audit,
    configuration,
    conversation,
    dataset,
    evaluation,
    experiment,
    knowledge,
    memory,
    model_registry,
    notification,
    organization,
    plugin,
    prompt,
    session,
    user,
    workflow,
    workspace,
)

__all__ = [
    "agent",
    "audit",
    "configuration",
    "conversation",
    "dataset",
    "evaluation",
    "experiment",
    "knowledge",
    "model_registry",
    "notification",
    "organization",
    "plugin",
    "prompt",
    "session",
    "user",
    "workflow",
    "workspace",
    "memory",
]
