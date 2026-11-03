"""Per-rule-type destination resolution. Each resolver takes the
rule's `config` JSON blob plus the request `context` dict (headers,
path, region, and any caller-supplied health signals) and returns the
destination string to route to — or `None` if the rule doesn't apply
to this particular request, in which case the caller falls through to
the next-priority rule or the route's default target. Kept as plain
functions (not a class) since none of them hold state across calls;
only weighted/canary/split/mirror need randomness, injected by the
caller rather than imported here, so tests stay deterministic."""
from __future__ import annotations

from collections.abc import Callable


def _weighted_pick(weights: dict[str, float], rand_value: float) -> str:
    total = sum(weights.values()) or 1.0
    target = rand_value * total
    cumulative = 0.0
    for destination, weight in weights.items():
        cumulative += weight
        if target < cumulative:
            return destination
    return next(iter(weights))


def resolve_weighted(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    weights = config.get("weights", {})
    if not weights:
        return None
    return _weighted_pick(weights, rand())


def resolve_split(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    splits = config.get("splits", {})
    if not splits:
        return None
    return _weighted_pick(splits, rand())


def resolve_canary(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    stable = config.get("stable")
    canary = config.get("canary")
    percent = config.get("canary_percent", 0)
    if stable is None or canary is None:
        return None
    return canary if rand() * 100 < percent else stable


def resolve_blue_green(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    if config.get("cutover"):
        return config.get("candidate")
    return config.get("active")


def resolve_header(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    header = config.get("header")
    if header is None:
        return None
    headers = context.get("headers", {})
    if headers.get(header) == config.get("value"):
        return config.get("destination")
    return None


def resolve_path(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    prefix = config.get("prefix")
    if prefix is None:
        return None
    path = context.get("path", "")
    return config.get("destination") if path.startswith(prefix) else None


def resolve_region(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    region_map = config.get("region_map", {})
    region = context.get("region")
    return region_map.get(region, config.get("default"))


def resolve_priority(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    destinations = config.get("destinations", [])
    unhealthy = set(context.get("unhealthy_destinations", []))
    for destination in destinations:
        if destination not in unhealthy:
            return destination
    return None


def resolve_mirror(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    return config.get("primary")


def should_mirror(config: dict, rand: Callable[[], float]) -> str | None:
    """Separate from `resolve_mirror`'s primary-destination pick — a
    caller decides independently whether *this* request also gets
    mirrored to `mirror_to`, since mirroring never affects what the
    real response is served from."""
    if rand() < config.get("sample_rate", 1.0):
        return config.get("mirror_to")
    return None


def resolve_failover(config: dict, context: dict, rand: Callable[[], float]) -> str | None:
    if context.get("primary_healthy", True):
        return config.get("primary")
    return config.get("fallback")


RESOLVERS: dict[str, Callable[[dict, dict, Callable[[], float]], str | None]] = {
    "weighted": resolve_weighted,
    "split": resolve_split,
    "canary": resolve_canary,
    "blue_green": resolve_blue_green,
    "header": resolve_header,
    "path": resolve_path,
    "region": resolve_region,
    "priority": resolve_priority,
    "mirror": resolve_mirror,
    "failover": resolve_failover,
}
