"""Live smoke test against running services (scripts/dev.py or docker compose).

    python scripts/smoke_test.py
    AIOS_INTERNAL_TOKEN=... python scripts/smoke_test.py

Checks, over real HTTP:
  1. every service answers /health/ready with 200;
  2. writes persist: in each service with a workspaces API, a workspace created in one request can be read back,
     by id and by organisation, in the next (unit tests cannot see a missing per-request commit; this can);
  3. with AIOS_INTERNAL_TOKEN set, a request without the token is refused with 401 while /health stays open.
Exit status is non-zero on any failure.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

HOST = os.environ.get("AIOS_SERVICE_HOST", "127.0.0.1")
TOKEN = os.environ.get("AIOS_INTERNAL_TOKEN", "")
PORTS = range(8000, 8020)
WORKSPACE_SERVICES = {"prompt": 8002, "agent": 8003, "memory": 8004, "workflow": 8005, "tool": 8006, "evaluation": 8007}


def request(method: str, port: int, path: str, body: dict | None = None, *, token: str | None = TOKEN):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Internal-Token"] = token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://{HOST}:{port}{path}", data=data, method=method, headers=headers)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - local services
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")[:200]
    except OSError as exc:
        return 0, str(exc)


def main() -> int:
    failures: list[str] = []

    down = [p for p in PORTS if request("GET", p, "/health/ready", token=None)[0] != 200]
    print(f"readiness     {len(PORTS) - len(down)}/{len(PORTS)} services ready" + (f"; not ready: {down}" if down else ""))
    failures += [f"port {p} not ready" for p in down]

    for name, port in WORKSPACE_SERVICES.items():
        org = f"smoke-{uuid.uuid4().hex[:10]}"
        status, ws = request("POST", port, "/api/v1/workspaces", {"name": "Smoke", "slug": org, "organization_id": org})
        if status != 201:
            failures.append(f"{name}: create workspace -> {status} {ws}")
            continue
        by_id = request("GET", port, f"/api/v1/workspaces/{ws['id']}")[0]
        listed = request("GET", port, f"/api/v1/workspaces?organization_id={org}")[1]
        ok = by_id == 200 and isinstance(listed, list) and len(listed) == 1
        print(f"persistence   {name:11} {'ok' if ok else f'LOST (get {by_id}, list {listed!r})'}")
        if not ok:
            failures.append(f"{name}: write did not persist")

    if TOKEN:
        refused = request("GET", 8003, "/api/v1/agent-types", token=None)[0]
        wrong = request("GET", 8003, "/api/v1/agent-types", token=TOKEN[:-1] + "x")[0]
        health = request("GET", 8003, "/health", token=None)[0]
        ok = refused == 401 and wrong == 401 and health == 200
        print(f"edge guard    no token {refused}, wrong token {wrong}, /health {health}: {'ok' if ok else 'FAIL'}")
        if not ok:
            failures.append("edge guard not enforced")
    else:
        print("edge guard    skipped (AIOS_INTERNAL_TOKEN not set)")

    print("\nPASS" if not failures else "\nFAIL\n  " + "\n  ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
