"""Pure semantic-versioning helpers — no DB or service imports, so
these are trivially unit-testable in isolation. Deliberately a
minimal, spec-adjacent subset of full SemVer 2.0.0: parses
`major.minor.patch[-prerelease][+build]`, compares by (major, minor,
patch, prerelease) with build metadata ignored for ordering (per the
SemVer spec, build metadata must not factor into precedence), and a
missing prerelease sorts *after* any present prerelease (a stable
release outranks any of its own release candidates)."""
from __future__ import annotations

import re
from dataclasses import dataclass

_SEMVER_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:-(?P<prerelease>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


@dataclass(frozen=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    prerelease: str | None
    build: str | None


class InvalidSemVerError(ValueError):
    pass


def parse_version(version: str) -> ParsedVersion:
    match = _SEMVER_RE.match(version.strip())
    if not match:
        raise InvalidSemVerError(f"'{version}' is not a valid semantic version")
    return ParsedVersion(
        major=int(match.group("major")), minor=int(match.group("minor")), patch=int(match.group("patch")),
        prerelease=match.group("prerelease"), build=match.group("build"),
    )


def _sort_key(v: ParsedVersion) -> tuple:
    # A version with no prerelease outranks one with a prerelease at the
    # same (major, minor, patch); among prereleases, plain string
    # comparison is a reasonable approximation of SemVer's dot-separated
    # identifier comparison for this platform's purposes.
    return (v.major, v.minor, v.patch, 1 if v.prerelease is None else 0, v.prerelease or "")


def compare_versions(a: str, b: str) -> int:
    """Returns -1 if a < b, 0 if equal (ignoring build metadata), 1 if a > b."""
    key_a, key_b = _sort_key(parse_version(a)), _sort_key(parse_version(b))
    if key_a < key_b:
        return -1
    if key_a > key_b:
        return 1
    return 0


def is_compatible(candidate: str, *, compatible_from: str, compatible_to: str | None = None) -> bool:
    if compare_versions(candidate, compatible_from) < 0:
        return False
    if compatible_to is not None and compare_versions(candidate, compatible_to) > 0:
        return False
    return True
