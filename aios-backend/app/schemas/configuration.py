from typing import Any

from pydantic import BaseModel


class ConfigurationSetRequest(BaseModel):
    key: str
    value: Any


class ConfigurationRead(BaseModel):
    key: str
    value: Any
