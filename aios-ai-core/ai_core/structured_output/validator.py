"""Validates parsed JSON against the caller's Pydantic output model."""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ai_core.utils.exceptions import StructuredOutputError

T = TypeVar("T", bound=BaseModel)


def validate_against_model(data: dict | list, output_model: type[T]) -> T:
    try:
        return output_model.model_validate(data)
    except ValidationError as exc:
        raise StructuredOutputError(f"response did not match {output_model.__name__} schema: {exc}") from exc
