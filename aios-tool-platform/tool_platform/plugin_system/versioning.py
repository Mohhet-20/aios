"""Minimal semver-ish constraint checking for plugin dependencies.
Supports exact versions ("1.2.0"), "*" (any), and ">=", "<=", ">", "<",
"^" (compatible-with, same major) prefixes — enough for a dependency
graph without pulling in a full semver library."""
from __future__ import annotations

from tool_platform.core.exceptions import ValidationError


def _parse(version: str) -> tuple[int, int, int]:
    parts = version.strip().split(".")
    parts += ["0"] * (3 - len(parts))
    try:
        return tuple(int(p) for p in parts[:3])  # type: ignore[return-value]
    except ValueError as exc:
        raise ValidationError(f"'{version}' is not a valid semver-style version") from exc


def satisfies(version: str, constraint: str) -> bool:
    constraint = constraint.strip()
    if constraint in ("", "*"):
        return True
    if constraint.startswith(">="):
        return _parse(version) >= _parse(constraint[2:])
    if constraint.startswith("<="):
        return _parse(version) <= _parse(constraint[2:])
    if constraint.startswith(">"):
        return _parse(version) > _parse(constraint[1:])
    if constraint.startswith("<"):
        return _parse(version) < _parse(constraint[1:])
    if constraint.startswith("^"):
        target = _parse(constraint[1:])
        actual = _parse(version)
        return actual[0] == target[0] and actual >= target
    return _parse(version) == _parse(constraint)
