"""ResourceLimits: the CPU/memory/disk/time budget a sandboxed execution
is allowed to consume, and SandboxResult: what it actually measured
using it — the same "only report genuinely measured numbers" honesty
principle the Workflow Engine's observability module follows. Defaults
come from `Settings` so a workspace/tool-version can override them
per-call without the sandbox needing to know about configuration at all."""
from __future__ import annotations

from dataclasses import dataclass, field

from tool_platform.config.settings import Settings, get_settings


@dataclass(frozen=True)
class ResourceLimits:
    cpu_seconds: int = 30
    memory_mb: int = 512
    disk_mb: int = 256
    timeout_seconds: int = 30

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> "ResourceLimits":
        s = settings or get_settings()
        return cls(
            cpu_seconds=s.sandbox_default_cpu_seconds, memory_mb=s.sandbox_default_memory_limit_mb,
            disk_mb=s.sandbox_default_disk_limit_mb, timeout_seconds=s.sandbox_default_timeout_seconds,
        )


@dataclass
class SandboxResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    timed_out: bool = False
    resource_limit_exceeded: bool = False
    wall_time_ms: float = 0.0
    cpu_seconds: float | None = None
    peak_memory_mb: float | None = None
    output_data: dict = field(default_factory=dict)
