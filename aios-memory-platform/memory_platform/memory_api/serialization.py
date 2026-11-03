"""Lightweight ORM -> JSON-safe dict serialization. Pulls only mapped
columns (never relationship attributes), so it's recursion-safe by
construction and needs no per-model schema — FastAPI's own
`jsonable_encoder` handles datetime/enum conversion for whatever this
returns. Request bodies are still validated with real Pydantic models
(see each router); this is deliberately just for the read side.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_dict(obj: Any) -> dict | None:
    if obj is None:
        return None
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if hasattr(obj, "__table__"):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    raise TypeError(f"to_dict() does not know how to serialize {type(obj)!r}")


def to_dict_list(objs: list) -> list[dict]:
    return [to_dict(o) for o in objs]
