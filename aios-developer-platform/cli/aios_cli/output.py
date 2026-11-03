"""Output formatting shared by every command: `table` (human-readable,
the default) or `json` (machine-readable, for scripting/CI). Every
command funnels its result rows through `render` so switching a
user's default format via `aios config set output_format json`
changes every command at once."""
from __future__ import annotations

import json as json_lib

import click


def render(rows: list[dict], *, fmt: str = "table", columns: list[str] | None = None) -> None:
    if not rows:
        click.echo("(no results)")
        return
    if fmt == "json":
        click.echo(json_lib.dumps(rows, indent=2, default=str))
        return

    columns = columns or list(rows[0].keys())
    widths = {col: max(len(col), *(len(str(row.get(col, ""))) for row in rows)) for col in columns}
    header = "  ".join(col.upper().ljust(widths[col]) for col in columns)
    click.echo(header)
    click.echo("  ".join("-" * widths[col] for col in columns))
    for row in rows:
        click.echo("  ".join(str(row.get(col, "")).ljust(widths[col]) for col in columns))


def render_one(row: dict, *, fmt: str = "table") -> None:
    if fmt == "json":
        click.echo(json_lib.dumps(row, indent=2, default=str))
        return
    width = max(len(k) for k in row) if row else 0
    for key, value in row.items():
        click.echo(f"{key.ljust(width)} : {value}")
