"""Fail if the per-service copies of a shared module have drifted apart.

Services stay independently deployable, so small cross-cutting modules are copied into each one instead of
being a shared package. This check keeps those copies byte-identical:

    python scripts/check_shared_modules.py
"""

from __future__ import annotations

import hashlib
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ("edge_guard.py", "clock.py")


def main() -> int:
    failed = False
    for name in SHARED:
        copies = [p for p in ROOT.glob(f"aios-*/**/{name}") if ".venv" not in p.parts and "node_modules" not in p.parts]
        by_hash: dict[str, list[Path]] = defaultdict(list)
        for path in copies:
            by_hash[hashlib.sha256(path.read_bytes()).hexdigest()].append(path)
        if len(by_hash) > 1:
            failed = True
            print(f"{name}: {len(by_hash)} different versions across {len(copies)} copies")
            for digest, paths in by_hash.items():
                print(f"  {digest[:12]}  " + ", ".join(str(p.relative_to(ROOT)) for p in paths))
        else:
            print(f"{name}: {len(copies)} identical copies")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
