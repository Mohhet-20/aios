"""Build the hosted public demo's showcase (run once, at image build time, by deploy/demo/Dockerfile).

Starts all twenty services in one process (deploy/demo/combined.py), exactly as the demo serves them, and seeds them
through their public REST APIs only with scripts/seed_demo.py: the Northwind Operations demo organisation with its
agents, prompts, workflows, tools, evaluations and datasets. Then adds the guest account behind the console's
"Explore the live demo": an ordinary member of that organisation, with no administrative role.

Both accounts get random passwords that are never printed or stored, so nobody can sign in with them; the guest is
reached only through POST /auth/guest, and the owner's password can be set at start from a hosting secret
(deploy/demo/demo_start.py). Leaves the twenty service databases in AIOS_DEMO_ROOT (default /tmp/aios-demo).
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO_ROOT = Path(os.environ.get("AIOS_DEMO_ROOT", "/tmp/aios-demo"))
PORT = 8790
BASE = f"http://127.0.0.1:{PORT}/svc"
OWNER_EMAIL = "demo@aios.dev"
GUEST_EMAIL = "guest@aios.dev"


def _wait_ready(proc: subprocess.Popen, names: list[str]) -> None:
    deadline = time.monotonic() + 180
    pending = list(names)
    while pending and time.monotonic() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"[demo-build] the platform exited with {proc.returncode} while starting")
        try:
            with urllib.request.urlopen(f"{BASE}/{pending[0]}/health/ready", timeout=3) as r:  # noqa: S310 - localhost
                if r.status == 200:
                    pending.pop(0)
                    continue
        except OSError:
            pass
        time.sleep(0.5)
    if pending:
        raise SystemExit(f"[demo-build] services not ready: {pending}")


def main() -> int:
    if DEMO_ROOT.exists():
        shutil.rmtree(DEMO_ROOT)
    DEMO_ROOT.mkdir(parents=True)
    token = secrets.token_urlsafe(32)
    env = {
        **os.environ,
        "APP_ENV": "production",
        "SECRET_KEY": secrets.token_urlsafe(48),  # build-only; the hosted instance signs with its own key
        "AIOS_INTERNAL_TOKEN": token,
        "LOG_LEVEL": "WARNING",
    }
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from combined import SERVICES

    proc = subprocess.Popen(  # noqa: S603 - fixed argv
        [sys.executable, "-m", "uvicorn", "--app-dir", str(Path(__file__).resolve().parent), "combined:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        cwd=DEMO_ROOT, env=env,
    )
    try:
        _wait_ready(proc, list(SERVICES))
        print(f"[demo-build] all {len(SERVICES)} services ready", flush=True)

        seed_env = {**env, "AIOS_SERVICES_BASE_URL": BASE, "AIOS_DEMO_EMAIL": OWNER_EMAIL,
                    "AIOS_DEMO_PASSWORD": secrets.token_urlsafe(24) + "!A1"}
        seeded = subprocess.run(  # noqa: S603 - fixed argv
            [sys.executable, str(ROOT / "scripts" / "seed_demo.py")], env=seed_env, capture_output=True, text=True,
        )
        for line in seeded.stdout.splitlines():
            if line.strip() and not line.startswith("Demo account"):  # never echo the (random) password
                print(f"[demo-build] {line}", flush=True)
        if seeded.returncode != 0:
            raise SystemExit(f"[demo-build] seeding failed: {seeded.stderr[-800:]}")

        def call(method: str, path: str, body: dict | None = None):
            req = urllib.request.Request(  # noqa: S310 - localhost
                f"{BASE}/identity{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
                headers={"Content-Type": "application/json", "X-Internal-Token": token},
            )
            with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
                raw = r.read()
                return json.loads(raw) if raw else None

        owner_password = seed_env["AIOS_DEMO_PASSWORD"]
        org_id = call("POST", "/api/v1/auth/login", {"email": OWNER_EMAIL, "password": owner_password})["primary_organization_id"]
        reg = call("POST", "/api/v1/auth/register",
                   {"email": GUEST_EMAIL, "password": secrets.token_urlsafe(24) + "!A1", "display_name": "Guest"})
        call("POST", "/api/v1/auth/verify-email", {"token": reg["verification_token"]})
        call("POST", f"/api/v1/memberships/organizations/{org_id}", {"user_id": reg["user"]["id"]})
        print(f"[demo-build] guest {GUEST_EMAIL} added to the demo organisation as a member", flush=True)
    finally:
        proc.terminate()
        proc.wait(timeout=30)
    print(f"[demo-build] showcase ready in {DEMO_ROOT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
