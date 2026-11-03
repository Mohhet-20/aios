"""Generates a real Python client module + typed models module from
an OpenAPI 3.0 document — walks `spec["paths"]` for operations and
`spec["components"]["schemas"]` for models. Output is plain,
syntactically valid Python (verified by the codegen engine via
`ast.parse` before it's ever persisted as an artifact), deliberately
shaped like the hand-written reference SDK (`sdks/python/aios_dev_sdk`)
so generated and hand-written clients feel like the same library."""
from __future__ import annotations

from developer_platform.codegen.generators.schema_types import operation_method_name, python_type_for


def _generate_models(schemas: dict[str, dict]) -> str:
    lines = [
        '"""Auto-generated typed models. Do not edit by hand — regenerate',
        'from the platform\'s OpenAPI schema instead."""',
        "from __future__ import annotations", "", "from dataclasses import dataclass", "",
    ]
    for name, schema in schemas.items():
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines.append("@dataclass")
        lines.append(f"class {name}:")
        if not properties:
            lines.append("    pass")
        else:
            # Required fields first (dataclasses require non-default fields before defaulted ones).
            for field_name in [f for f in properties if f in required]:
                field_type = python_type_for(properties[field_name].get("type"))
                lines.append(f"    {field_name}: {field_type}")
            for field_name in [f for f in properties if f not in required]:
                field_type = python_type_for(properties[field_name].get("type"))
                lines.append(f"    {field_name}: {field_type} | None = None")
        lines.append("")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _generate_client(spec: dict) -> str:
    lines = [
        '"""Auto-generated API client. Do not edit by hand — regenerate',
        'from the platform\'s OpenAPI schema instead."""',
        "from __future__ import annotations", "", "from typing import Any", "", "import httpx", "",
        "", "class GeneratedClient:", '    """Generated from: ' + spec.get("info", {}).get("title", "AIOS API") + '"""', "",
        "    def __init__(self, base_url: str, api_key: str | None = None, *, timeout: float = 30.0):",
        "        self.base_url = base_url.rstrip('/')",
        "        headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}",
        "        self._client = httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout)", "",
    ]
    for path, operations in spec.get("paths", {}).items():
        for method, operation in operations.items():
            method_name = operation_method_name(operation.get("operationId", f"{method}_{path}"))
            summary = operation.get("summary", "")
            lines.append(f"    def {method_name}(self, **kwargs: Any) -> httpx.Response:")
            if summary:
                lines.append(f'        """{summary}"""')
            lines.append(f"        return self._client.request('{method.upper()}', '{path}', **kwargs)")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class PythonClientGenerator:
    language = "python"

    def generate(self, spec: dict) -> dict[str, str]:
        schemas = spec.get("components", {}).get("schemas", {})
        return {
            "client.py": _generate_client(spec),
            "models.py": _generate_models(schemas),
        }
