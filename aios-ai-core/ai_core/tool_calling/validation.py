"""JSON-Schema validation of tool call arguments against the tool's
declared `parameters` schema — catches a model hallucinating an argument
name or type before the handler ever runs."""
from __future__ import annotations

import jsonschema

from ai_core.schemas.tools import ToolDefinition
from ai_core.utils.exceptions import ToolExecutionError


def validate_tool_arguments(tool: ToolDefinition, arguments: dict) -> None:
    try:
        jsonschema.validate(instance=arguments, schema=tool.parameters)
    except jsonschema.ValidationError as exc:
        raise ToolExecutionError(f"arguments for tool '{tool.name}' failed schema validation: {exc.message}", tool_name=tool.name) from exc
    except jsonschema.SchemaError as exc:
        raise ToolExecutionError(f"tool '{tool.name}' has an invalid parameters schema: {exc.message}", tool_name=tool.name) from exc
