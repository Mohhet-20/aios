"""Lightweight ORM -> JSON-safe dict serialization. Pulls only mapped
columns (never relationship attributes), so it's recursion-safe by
construction and needs no per-model schema — FastAPI's own
`jsonable_encoder` handles datetime/enum conversion for whatever this
returns. Request bodies are still validated with real Pydantic models
(see each router); this is deliberately just for the read side, where
hand-writing ~30 response schemas would trade a lot of time for very
little safety given every field already has a typed column at the ORM
layer.
"""
from __future__ import annotations

from typing import Any


def to_dict(obj: Any) -> dict | None:
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def to_dict_list(objs: list) -> list[dict]:
    return [to_dict(o) for o in objs]
