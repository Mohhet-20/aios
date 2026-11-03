"""DatabaseQueryHandler: genuinely executes a parameterized query against
a real SQLite database via `aiosqlite` — not mocked. Backs
`connector_key="database_query"`, which the category registry wires up
for DATABASE_QUERY, SQL, NOSQL, VECTOR_DATABASE, and KNOWLEDGE_GRAPH.
Those last three are, honestly, not what this reference implementation
actually does differently — a real deployment would swap in a real
NoSQL/vector-DB/graph-DB driver behind the same `connector_key`, the
same way `ai_bridges` in the Workflow Engine swaps a reference bridge
for a real platform call. What's here is the one category (relational
SQL) this platform can genuinely execute end-to-end without an external
service dependency."""
from __future__ import annotations

from typing import Any

import aiosqlite

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


class DatabaseQueryHandler(ConnectorHandler):
    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        connection_string = ctx.config.get("connection_string") or (ctx.credential_secret or {}).get("connection_string")
        query = ctx.input_data.get("query")
        if not connection_string:
            raise ToolExecutionError("database_query tool call requires a 'connection_string' in config or credential")
        if not query:
            raise ToolExecutionError("database_query tool call requires a 'query'")

        params = ctx.input_data.get("params") or []
        async with aiosqlite.connect(connection_string) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            if query.strip().lower().startswith("select"):
                rows = await cursor.fetchall()
                return {"rows": [dict(r) for r in rows], "row_count": len(rows)}
            await db.commit()
            return {"rows_affected": cursor.rowcount}
