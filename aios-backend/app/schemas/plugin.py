from pydantic import BaseModel

from app.schemas.common import TimestampedRead


class PluginManifestRead(BaseModel):
    id: str
    name: str
    version: str
    category: str
    description: str
    provides_tools: list[str]
    provides_graders: list[str]


class PluginInstallRequest(BaseModel):
    plugin_manifest_id: str


class PluginRead(TimestampedRead):
    organization_id: str
    name: str
    category: str
    version: str
    enabled: bool


class ToolRead(TimestampedRead):
    organization_id: str
    name: str
    description: str
    category: str
    side_effect: str
    verified: bool
    installs: int
