"""Fail if a service injects its committing database session without ``scope="function"``.

Each service's session dependency commits after the handler returns. FastAPI's default scope for a ``yield``
dependency runs that code *after* the response has been sent, so a client could act on a 2xx before the write was
committed (the next request then misses it), and a failed commit would follow a response that already said
"success". ``Depends(get_session, scope="function")`` commits first, then responds. In-process test clients wait
for the whole request either way, so the test suites cannot see the difference; this check keeps it from regressing:

    python scripts/check_commit_before_response.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNSCOPED = re.compile(r"Depends\(\s*(get_session|get_db_session|get_db|get_uow|get_unit_of_work)\s*\)")


def main() -> int:
    bad = []
    for path in ROOT.glob("aios-*/**/*.py"):
        if {".venv", "node_modules", "tests"} & set(path.parts):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if UNSCOPED.search(line):
                bad.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    if bad:
        print('Session dependencies without scope="function" (commit would run after the response):')
        print("\n".join(f"  {b}" for b in bad))
        return 1
    print("every committing session dependency commits before the response")
    return 0


if __name__ == "__main__":
    sys.exit(main())
