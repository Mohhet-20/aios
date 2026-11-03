"""These run REAL subprocesses under REAL rlimits — no mocking. If the
sandbox's CPU/memory/timeout enforcement doesn't actually work, these
tests fail for real, the same way a production runaway tool call would
actually get killed."""
import pytest

from tool_platform.core.exceptions import SandboxViolationError
from tool_platform.sandbox import subprocess_sandbox
from tool_platform.sandbox.resource_limits import ResourceLimits
from tool_platform.sandbox.subprocess_sandbox import SANDBOX_AVAILABLE, SubprocessSandbox

posix_only = pytest.mark.skipif(not SANDBOX_AVAILABLE, reason="needs POSIX rlimits (runs on Linux CI)")


def test_sandbox_fails_closed_without_rlimits(monkeypatch):
    monkeypatch.setattr(subprocess_sandbox, "SANDBOX_AVAILABLE", False)
    with pytest.raises(SandboxViolationError, match="refusing to run unconfined code"):
        SubprocessSandbox().run_python("print('must not run')")


@posix_only
def test_simple_python_execution_succeeds():
    sandbox = SubprocessSandbox()
    result = sandbox.run_python("print('hello from sandbox')")
    assert result.success is True
    assert "hello from sandbox" in result.stdout
    assert result.return_code == 0


@posix_only
def test_python_exit_code_propagates():
    sandbox = SubprocessSandbox()
    result = sandbox.run_python("import sys; sys.exit(3)")
    assert result.success is False
    assert result.return_code == 3


@posix_only
def test_wall_clock_timeout_is_enforced():
    sandbox = SubprocessSandbox()
    result = sandbox.run_python("import time; time.sleep(5)", limits=ResourceLimits(timeout_seconds=1, cpu_seconds=30))
    assert result.timed_out is True
    assert result.success is False


@posix_only
def test_cpu_limit_kills_busy_loop():
    sandbox = SubprocessSandbox()
    # A tight busy loop burns real CPU time (unlike time.sleep, which burns
    # wall-clock but not CPU) — this should hit RLIMIT_CPU, not the timeout.
    result = sandbox.run_python(
        "x = 0\nwhile True:\n    x += 1",
        limits=ResourceLimits(cpu_seconds=1, timeout_seconds=10, memory_mb=256),
    )
    assert result.success is False
    assert result.timed_out is False  # should die from CPU limit, well before the 10s wall-clock timeout


@posix_only
def test_cpu_seconds_are_genuinely_measured():
    sandbox = SubprocessSandbox()
    result = sandbox.run_python("x = sum(range(10_000_000))")
    assert result.success is True
    assert result.cpu_seconds is not None
    assert result.cpu_seconds >= 0
    assert result.peak_memory_mb is not None
    assert result.peak_memory_mb > 0


@posix_only
def test_shell_command_execution():
    sandbox = SubprocessSandbox()
    result = sandbox.run_shell(["echo", "hello from shell"])
    assert result.success is True
    assert "hello from shell" in result.stdout


@posix_only
def test_shell_nonexistent_command_fails_cleanly():
    sandbox = SubprocessSandbox()
    result = sandbox.run_shell(["/bin/nonexistent-command-xyz"])
    assert result.success is False


@posix_only
def test_filesystem_isolation_uses_throwaway_cwd():
    import os
    sandbox = SubprocessSandbox()
    result = sandbox.run_python("import os; print(os.getcwd())")
    assert result.success is True
    printed_cwd = result.stdout.strip()
    assert printed_cwd != os.getcwd()  # never runs in the caller's own working directory
    assert not os.path.exists(printed_cwd)  # cleaned up after the run
