"""Thin wrapper around `croniter` — the one place this platform parses a
cron expression, so swapping the underlying library later touches one
file. Standard 5-field cron syntax (`* * * * *`)."""
from __future__ import annotations

from datetime import datetime

from croniter import CroniterBadCronError, croniter

from tool_platform.core.exceptions import ValidationError


def validate_cron_expression(expression: str) -> None:
    if not croniter.is_valid(expression):
        raise ValidationError(f"invalid cron expression: '{expression}'")


def next_fire_time(expression: str, *, after: datetime) -> datetime:
    try:
        return croniter(expression, after).get_next(datetime)
    except (CroniterBadCronError, ValueError) as exc:
        raise ValidationError(f"invalid cron expression: '{expression}'") from exc
