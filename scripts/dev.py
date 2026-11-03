"""Run AIOS services locally without Docker: one uvicorn process per service, SQLite, same host ports as Compose.

    python scripts/dev.py                     # every backend service
    python scripts/dev.py identity agent      # only services whose name contains one of these
    python scripts/dev.py --list              # print the service map and exit

Each service keeps its SQLite file under var/<service>/. Waits for every /health/ready, prints a status table,
then streams nothing and keeps running until Ctrl+C, which stops all children. Use the interpreter of a virtualenv
that has the services' requirements installed (see README: "Run without Docker").
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# service directory -> (host port, uvicorn target, is factory). Ports match docker-compose.yml.
SERVICES: dict[str, tuple[int, str, bool]] = {
    "aios-backend": (8000, "app.main:app", False),
    "aios-ai-core": (8001, "ai_core.main:app", False),
    "aios-prompt-platform": (8002, "prompt_platform.main:app", False),
    "aios-agent-platform": (8003, "agent_platform.main:app", False),
    "aios-memory-platform": (8004, "memory_platform.main:app", False),
    "aios-workflow-engine": (8005, "workflow_platform.workflow_api.application_factory:create_app", True),
    "aios-tool-platform": (8006, "tool_platform.tool_api.application_factory:create_app", True),
    "aios-evaluation-platform": (8007, "eval_platform.eval_api.application_factory:create_app", True),
    "aios-identity-platform": (8008, "identity_platform.identity_api.application_factory:create_app", True),
    "aios-collaboration-platform": (8009, "collaboration_platform.collab_api.application_factory:create_app", True),
    "aios-observability-platform": (8010, "observability_platform.obs_api.application_factory:create_app", True),
    "aios-security-platform": (8011, "security_platform.sec_api.application_factory:create_app", True),
    "aios-infrastructure-platform": (8012, "infra_platform.infra_api.application_factory:create_app", True),
    "aios-developer-platform": (8013, "developer_platform.dev_api.application_factory:create_app", True),
    "aios-api-gateway-platform": (8014, "gateway_platform.gw_api.application_factory:create_app", True),
    "aios-analytics-platform": (8015, "analytics_platform.an_api.application_factory:create_app", True),
    "aios-quality-platform": (8016, "quality_platform.qa_api.application_factory:create_app", True),
    "aios-docs-platform": (8017, "docs_platform.doc_api.application_factory:create_app", True),
    "aios-release-platform": (8018, "release_platform.release_api.application_factory:create_app", True),
    "aios-perf-platform": (8019, "perf_platform.perf_api.application_factory:create_app", True),
}


def ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/ready", timeout=2) as r:  # noqa: S310 - localhost
            return r.status == 200
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("filters", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--timeout", type=float, default=90.0, help="seconds to wait for readiness")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # status lines appear immediately even when redirected

    chosen = {k: v for k, v in SERVICES.items() if not args.filters or any(f in k for f in args.filters)}
    if args.list:
        for name, (port, target, _) in chosen.items():
            print(f"{name:30} http://127.0.0.1:{port}   {target}")
        return 0

    procs: dict[str, subprocess.Popen[bytes]] = {}
    logs = ROOT / "var" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    for name, (port, target, factory) in chosen.items():
        data = ROOT / "var" / name
        data.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "PYTHONPATH": str(ROOT / name), "AIOS_DEV_DATA_DIR": str(data)}
        cmd = [sys.executable, "-m", "uvicorn", target, "--host", "127.0.0.1", "--port", str(port)]
        if factory:
            cmd.append("--factory")
        log = open(logs / f"{name}.log", "wb")  # noqa: SIM115 - kept open for the child's lifetime
        # cwd is the data directory, so each service's default sqlite:///./<name>.db lands under var/<service>/.
        procs[name] = subprocess.Popen(cmd, cwd=data, env=env, stdout=log, stderr=subprocess.STDOUT)  # noqa: S603

    deadline = time.monotonic() + args.timeout
    status: dict[str, str] = {}
    while time.monotonic() < deadline and len(status) < len(procs):
        for name, proc in procs.items():
            if name in status:
                continue
            if proc.poll() is not None:
                status[name] = f"EXITED ({proc.returncode}) - see var/logs/{name}.log"
            elif ready(chosen[name][0]):
                status[name] = "ready"
        time.sleep(0.5)
    for name in procs:
        status.setdefault(name, f"NOT READY after {args.timeout:.0f}s - see var/logs/{name}.log")

    for name, (port, _, _) in chosen.items():
        print(f"{name:30} :{port}  {status[name]}")
    up = sum(1 for s in status.values() if s == "ready")
    print(f"\n{up}/{len(procs)} services ready. API docs: http://127.0.0.1:<port>/docs. Ctrl+C to stop.")

    def stop(*_: object) -> None:
        for proc in procs.values():
            if proc.poll() is None:
                proc.terminate()
        for proc in procs.values():
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        raise SystemExit(0 if up == len(procs) else 1)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    raise SystemExit(main())
