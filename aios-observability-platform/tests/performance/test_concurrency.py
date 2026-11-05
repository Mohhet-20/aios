"""Real concurrency stress tests: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every other AIOS
services. `AlertEvaluationService.fire_or_update`/
`auto_resolve_if_healed` are this platform's one commit-spanning-lock
check-then-act sequence (see that module's docstring); this test
proves the per-dedup-key `asyncio.Lock` actually prevents the alert
duplication a naive "check then insert" would produce under real
concurrent rule evaluation (e.g. several worker processes evaluating
the same rule against the same component in the same tick)."""
from __future__ import annotations

import asyncio

import pytest

from observability_platform.alerts.evaluation_service import AlertEvaluationService
from observability_platform.database.session import session_scope
from observability_platform.models.alerts import AlertRuleModel
from observability_platform.repositories.registry import RepositoryRegistry

TENANT = "stress-tenant"


async def _create_rule() -> str:
    # Never `return` from inside `async for session in session_scope():
    # ...` — that closes the generator via GeneratorExit without
    # resuming past the `yield`, silently skipping the post-yield
    # commit (documented in `database/session.py`). Capture the result
    # in an outer variable and return only after the loop completes.
    rule_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        rule = await repos.alert_rules.add(
            AlertRuleModel(
                tenant_id=TENANT, name="stress-rule", alert_type="threshold", metric_name="stress_metric",
                condition={"operator": "gt", "value": 0},
            )
        )
        rule_id = rule.id
    return rule_id


async def _fire_once(rule_id: str) -> str:
    alert_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        rule = await repos.alert_rules.get_or_404(rule_id)
        svc = AlertEvaluationService(repos)
        alert = await svc.fire_or_update(TENANT, rule, component_id="stress-component", context={"value": 99})
        alert_id = alert.id
    return alert_id


@pytest.mark.asyncio
async def test_concurrent_alert_firing_does_not_duplicate():
    rule_id = await _create_rule()

    results = await asyncio.gather(*[_fire_once(rule_id) for _ in range(15)])

    # Every concurrent caller should have been serialized onto the SAME
    # alert row (same id) rather than each creating its own — this is
    # exactly the bug an unlocked "check active, then insert" sequence
    # would produce under real concurrency.
    assert len(set(results)) == 1

    active = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        active = await repos.alerts.list_by_status(TENANT, "firing")
    assert len(active) == 1
