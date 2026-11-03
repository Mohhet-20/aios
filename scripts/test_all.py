"""Run every backend service's test suite, each from its own directory, and print one summary table.

    python scripts/test_all.py                 # all services
    python scripts/test_all.py ai-core tool    # only services whose name contains one of these
    python scripts/test_all.py --junit DIR     # also write DIR/<service>.xml

Exit status is non-zero if any suite fails. Uses the interpreter it runs under, so activate the shared virtualenv
(or one with the services' requirements installed) first.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def services(filters: list[str]) -> list[Path]:
    found = sorted(p for p in ROOT.glob("aios-*") if (p / "tests").is_dir() and (p / "pyproject.toml").is_file())
    return [p for p in found if not filters or any(f in p.name for f in filters)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("filters", nargs="*")
    ap.add_argument("--junit", type=Path)
    args = ap.parse_args()
    if args.junit:
        args.junit.mkdir(parents=True, exist_ok=True)

    rows: list[tuple[str, str, float]] = []
    failed = 0
    for svc in services(args.filters):
        cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"]
        if args.junit:
            cmd.append(f"--junitxml={(args.junit / f'{svc.name}.xml').resolve()}")
        start = time.perf_counter()
        proc = subprocess.run(cmd, cwd=svc, capture_output=True, text=True)  # noqa: S603 - fixed argv
        took = time.perf_counter() - start
        tail = [ln for ln in proc.stdout.splitlines() if re.search(r"\b(passed|failed|error|no tests ran)\b", ln)]
        summary = tail[-1].strip("= ") if tail else f"exit {proc.returncode}"
        if proc.returncode != 0:
            failed += 1
            summary = "FAIL: " + summary
            sys.stderr.write(f"\n--- {svc.name} ---\n{proc.stdout[-4000:]}\n{proc.stderr[-2000:]}\n")
        rows.append((svc.name, summary, took))
        print(f"{svc.name:32} {summary}  ({took:.0f}s)", flush=True)

    total = sum(int(m.group(1)) for _, s, _ in rows for m in [re.search(r"(\d+) passed", s)] if m)
    print(f"\n{len(rows)} services, {total} tests passed, {failed} suite(s) failing")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
