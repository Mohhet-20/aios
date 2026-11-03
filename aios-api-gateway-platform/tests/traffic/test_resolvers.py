from __future__ import annotations

from gateway_platform.traffic.resolvers import (
    resolve_blue_green,
    resolve_canary,
    resolve_failover,
    resolve_header,
    resolve_path,
    resolve_priority,
    resolve_region,
    resolve_split,
    resolve_weighted,
    should_mirror,
)


def test_resolve_weighted_picks_by_rand():
    config = {"weights": {"a": 1, "b": 9}}
    assert resolve_weighted(config, {}, lambda: 0.05) == "a"
    assert resolve_weighted(config, {}, lambda: 0.95) == "b"


def test_resolve_weighted_empty_returns_none():
    assert resolve_weighted({"weights": {}}, {}, lambda: 0.5) is None


def test_resolve_split_behaves_like_weighted():
    config = {"splits": {"x": 50, "y": 50}}
    assert resolve_split(config, {}, lambda: 0.1) == "x"
    assert resolve_split(config, {}, lambda: 0.9) == "y"


def test_resolve_canary_respects_percent():
    config = {"stable": "v1", "canary": "v2", "canary_percent": 10}
    assert resolve_canary(config, {}, lambda: 0.05) == "v2"
    assert resolve_canary(config, {}, lambda: 0.50) == "v1"


def test_resolve_blue_green_cutover_flag():
    config = {"active": "blue", "candidate": "green", "cutover": False}
    assert resolve_blue_green(config, {}, lambda: 0.5) == "blue"
    config["cutover"] = True
    assert resolve_blue_green(config, {}, lambda: 0.5) == "green"


def test_resolve_header_matches_value():
    config = {"header": "X-Beta", "value": "true", "destination": "v2"}
    assert resolve_header(config, {"headers": {"X-Beta": "true"}}, lambda: 0.5) == "v2"
    assert resolve_header(config, {"headers": {"X-Beta": "false"}}, lambda: 0.5) is None
    assert resolve_header(config, {"headers": {}}, lambda: 0.5) is None


def test_resolve_path_prefix_match():
    config = {"prefix": "/beta", "destination": "v2"}
    assert resolve_path(config, {"path": "/beta/widgets"}, lambda: 0.5) == "v2"
    assert resolve_path(config, {"path": "/stable/widgets"}, lambda: 0.5) is None


def test_resolve_region_falls_back_to_default():
    config = {"region_map": {"us": "v1", "eu": "v2"}, "default": "v1"}
    assert resolve_region(config, {"region": "eu"}, lambda: 0.5) == "v2"
    assert resolve_region(config, {"region": "apac"}, lambda: 0.5) == "v1"


def test_resolve_priority_skips_unhealthy():
    config = {"destinations": ["v1", "v2", "v3"]}
    assert resolve_priority(config, {}, lambda: 0.5) == "v1"
    assert resolve_priority(config, {"unhealthy_destinations": ["v1"]}, lambda: 0.5) == "v2"


def test_resolve_failover_uses_primary_health():
    config = {"primary": "v1", "fallback": "v2"}
    assert resolve_failover(config, {"primary_healthy": True}, lambda: 0.5) == "v1"
    assert resolve_failover(config, {"primary_healthy": False}, lambda: 0.5) == "v2"


def test_should_mirror_respects_sample_rate():
    config = {"mirror_to": "shadow-svc", "sample_rate": 0.5}
    assert should_mirror(config, lambda: 0.1) == "shadow-svc"
    assert should_mirror(config, lambda: 0.9) is None
