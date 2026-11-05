"""Start the hosted public demo API (deploy/demo/Dockerfile): a fresh showcase, then all twenty services.

On every start this:

1. copies the showcase databases built by deploy/demo/demo_build.py to a fresh working directory, so each restart is
   a clean demo (the services' default SQLite files land there, one per service);
2. runs in production mode: SECRET_KEY (the identity service's signing key, shared with the console as
   AIOS_JWT_SECRET) and AIOS_INTERNAL_TOKEN (required by every service) come from hosting secrets;
3. enables the identity service's guest session for the demo organisation's ordinary member, guest@aios.dev;
4. when AIOS_OWNER_PASSWORD is set as a hosting secret (12+ characters, upper, lower, digit, symbol), makes it the
   password of the demo organisation's owner, demo@aios.dev, for the normal sign-in form; otherwise that account keeps
   the random password it was built with, which nobody knows;
5. replaces itself with uvicorn on $PORT.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHOWCASE = Path(os.environ.get("AIOS_SHOWCASE_DIR", "/app/showcase"))
WORKING = Path(os.environ.get("AIOS_DEMO_ROOT", "/tmp/aios-demo"))
OWNER_EMAIL = "demo@aios.dev"
GUEST_EMAIL = "guest@aios.dev"


def _set_owner_password(password: str) -> None:
    sys.path.insert(0, str(ROOT / "aios-identity-platform"))
    from identity_platform.security.hashing import hash_password

    db = sqlite3.connect(WORKING / "identity_platform.db")
    try:
        row = db.execute("SELECT id FROM ip_users WHERE email = ?", (OWNER_EMAIL,)).fetchone()
        if row is None:
            raise SystemExit(f"[demo] {OWNER_EMAIL} is missing from the showcase")
        db.execute("UPDATE ip_password_credentials SET password_hash = ?, previous_password_hashes = '[]' WHERE user_id = ?",
                   (hash_password(password), row[0]))
        db.commit()
    finally:
        db.close()


def main() -> int:
    if not (SHOWCASE / "identity_platform.db").is_file():
        print(f"[demo] {SHOWCASE} has no identity_platform.db; the image build did not produce the showcase", file=sys.stderr)
        return 2
    for key in ("SECRET_KEY", "AIOS_INTERNAL_TOKEN"):
        if len(os.environ.get(key, "")) < 32:
            print(f"[demo] {key} must be set (32+ characters) for the public demo", file=sys.stderr)
            return 2
    shutil.rmtree(WORKING, ignore_errors=True)  # the previous run's databases and their SQLite journals
    shutil.copytree(SHOWCASE, WORKING)
    os.environ.update({"APP_ENV": "production", "GUEST_ACCESS_ENABLED": "true", "GUEST_EMAIL": GUEST_EMAIL})

    password = os.environ.get("AIOS_OWNER_PASSWORD", "")
    if password:
        if len(password) < 12 or password.lower() == password or password.upper() == password \
                or not any(c.isdigit() for c in password) or password.isalnum():
            print("[demo] AIOS_OWNER_PASSWORD needs 12+ characters with upper, lower, digit and symbol", file=sys.stderr)
            return 2
        _set_owner_password(password)
        print(f"[demo] owner {OWNER_EMAIL} can sign in with AIOS_OWNER_PASSWORD", flush=True)
    else:
        print("[demo] AIOS_OWNER_PASSWORD not set: the owner account stays locked", flush=True)
    print("[demo] fresh showcase ready; guest access on; starting all twenty services", flush=True)

    os.environ.setdefault("FORWARDED_ALLOW_IPS", "*")  # behind the host's proxy
    os.chdir(WORKING)  # each service's default sqlite:///./<name>.db resolves here
    cmd = [sys.executable, "-m", "uvicorn", "--app-dir", str(HERE), "combined:app", "--host", "0.0.0.0",
           "--port", os.environ.get("PORT", "8000"), "--workers", "1", "--proxy-headers", "--no-access-log"]
    if os.name == "nt":  # local trial on Windows, where exec* mangles paths with spaces
        return subprocess.call(cmd)
    os.execvpe(cmd[0], cmd, os.environ)  # hand PID 1 to uvicorn so it receives SIGTERM
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
