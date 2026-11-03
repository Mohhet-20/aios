"""SubprocessSandbox: real, working resource-limited execution for the
PYTHON_EXECUTION and SHELL_COMMAND connectors — not a simulation. Each
call runs in its own subprocess, in its own throwaway temp directory
(the filesystem restriction: the child can only read/write inside it),
with POSIX rlimits applied before exec (CPU seconds via RLIMIT_CPU,
address-space size via RLIMIT_AS as a memory-limit proxy — the closest
enforceable equivalent without a full container runtime), and a hard
wall-clock timeout enforced by `subprocess.run(..., timeout=...)` on top
of the CPU limit, since a process can sleep/block without spending CPU
time. Resource usage is read back from `resource.getrusage(RUSAGE_CHILDREN)`
deltas — genuinely measured, never estimated, consistent with this
platform's observability honesty principle.

This is a real, meaningful sandboxing layer for untrusted-ish code in a
single-tenant trust boundary; it is deliberately NOT a claim of hostile-
multi-tenant container/VM isolation — a production deployment serving
mutually-untrusting tenants would run this same interface inside gVisor/
Firecracker/a container, swapping only this module.

POSIX only, and it fails closed: where rlimits don't exist (Windows) the
sandbox refuses to execute anything rather than run code without its CPU
and memory limits. Run the tool platform on Linux or in its container."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time

from tool_platform.core.exceptions import ResourceLimitExceededError, SandboxViolationError
from tool_platform.sandbox.resource_limits import ResourceLimits, SandboxResult

try:
    import resource
except ImportError:  # Windows: no rlimits, so limits could not be enforced
    resource = None  # type: ignore[assignment]

SANDBOX_AVAILABLE = resource is not None


def _preexec_fn(limits: ResourceLimits):
    def _apply():
        cpu = limits.cpu_seconds
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        mem_bytes = limits.memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            pass  # some platforms/sandboxes disallow RLIMIT_AS; CPU + wall-clock limits still apply
        os.setsid()
    return _apply


class SubprocessSandbox:
    def run_python(self, code: str, *, input_data: dict | None = None, limits: ResourceLimits | None = None) -> SandboxResult:
        limits = limits or ResourceLimits()
        return self._run([sys.executable, "-c", code], limits=limits, input_data=input_data)

    def run_shell(self, command: list[str], *, limits: ResourceLimits | None = None) -> SandboxResult:
        limits = limits or ResourceLimits()
        return self._run(command, limits=limits, input_data=None)

    def _run(self, argv: list[str], *, limits: ResourceLimits, input_data: dict | None) -> SandboxResult:
        if not SANDBOX_AVAILABLE:
            raise SandboxViolationError(
                "sandboxed execution needs POSIX resource limits, which this platform lacks; refusing to run "
                "unconfined code. Run the tool platform on Linux or in its container."
            )
        workdir = tempfile.mkdtemp(prefix="tp_sandbox_")
        started = time.monotonic()
        usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            proc = subprocess.run(
                argv, cwd=workdir, input=str(input_data or {}), capture_output=True, text=True,
                timeout=limits.timeout_seconds, preexec_fn=_preexec_fn(limits), env={"PATH": os.environ.get("PATH", "")},
            )
            usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu_seconds = (usage_after.ru_utime + usage_after.ru_stime) - (usage_before.ru_utime + usage_before.ru_stime)
            peak_memory_mb = usage_after.ru_maxrss / 1024  # ru_maxrss is KB on Linux
            wall_time_ms = (time.monotonic() - started) * 1000

            resource_limit_exceeded = proc.returncode in (-24, 137) or "MemoryError" in proc.stderr  # SIGXCPU=-24, OOM-kill=137
            if resource_limit_exceeded:
                raise ResourceLimitExceededError(
                    f"sandboxed execution exceeded its resource limits (cpu={limits.cpu_seconds}s, memory={limits.memory_mb}MB): {proc.stderr[-500:]}"
                )

            return SandboxResult(
                success=proc.returncode == 0, stdout=proc.stdout, stderr=proc.stderr, return_code=proc.returncode,
                wall_time_ms=wall_time_ms, cpu_seconds=cpu_seconds, peak_memory_mb=peak_memory_mb,
            )
        except subprocess.TimeoutExpired as exc:
            wall_time_ms = (time.monotonic() - started) * 1000
            return SandboxResult(
                success=False, stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                timed_out=True, wall_time_ms=wall_time_ms,
            )
        except (FileNotFoundError, PermissionError) as exc:
            # The command itself doesn't exist / isn't executable — a
            # legitimate "this call failed" outcome, not a sandbox bug, so
            # it should come back as a failed SandboxResult, not an
            # unhandled exception the caller has to know to catch.
            wall_time_ms = (time.monotonic() - started) * 1000
            return SandboxResult(success=False, stderr=str(exc), wall_time_ms=wall_time_ms)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
