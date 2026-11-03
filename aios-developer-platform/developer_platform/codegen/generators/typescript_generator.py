"""Generates a TypeScript client module + typed interfaces module from
the same OpenAPI 3.0 document the Python generator consumes — same
walk over `paths` and `components.schemas`, different target syntax,
so adding a third language later means adding a third generator that
implements the same `generate(spec) -> {file_path: content}` shape,
not touching this one."""
from __future__ import annotations

from developer_platform.codegen.generators.schema_types import operation_method_name, typescript_type_for


def _generate_models(schemas: dict[str, dict]) -> str:
    lines = ["// Auto-generated typed models. Do not edit by hand — regenerate", "// from the platform's OpenAPI schema instead.", ""]
    for name, schema in schemas.items():
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        lines.append(f"export interface {name} {{")
        for field_name, field_schema in properties.items():
            optional = "" if field_name in required else "?"
            field_type = typescript_type_for(field_schema.get("type"))
            lines.append(f"  {field_name}{optional}: {field_type};")
        lines.append("}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _generate_client(spec: dict) -> str:
    title = spec.get("info", {}).get("title", "AIOS API")
    lines = [
        "// Auto-generated API client. Do not edit by hand — regenerate",
        "// from the platform's OpenAPI schema instead.", "",
        f"// Generated from: {title}",
        "export class GeneratedClient {",
        "  private baseUrl: string;",
        "  private apiKey?: string;", "",
        "  constructor(baseUrl: string, apiKey?: string) {",
        "    this.baseUrl = baseUrl.replace(/\\/$/, '');",
        "    this.apiKey = apiKey;",
        "  }", "",
        "  private async request(method: string, path: string, body?: unknown): Promise<Response> {",
        "    const headers: Record<string, string> = this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {};",
        "    return fetch(`${this.baseUrl}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });",
        "  }", "",
    ]
    for path, operations in spec.get("paths", {}).items():
        for method, operation in operations.items():
            method_name = operation_method_name(operation.get("operationId", f"{method}_{path}"))
            summary = operation.get("summary", "")
            if summary:
                lines.append(f"  /** {summary} */")
            lines.append(f"  async {method_name}(body?: unknown): Promise<Response> {{")
            lines.append(f"    return this.request('{method.upper()}', '{path}', body);")
            lines.append("  }")
            lines.append("")
    lines.append("}")
    return "\n".join(lines).rstrip() + "\n"


class TypeScriptClientGenerator:
    language = "typescript"

    def generate(self, spec: dict) -> dict[str, str]:
        schemas = spec.get("components", {}).get("schemas", {})
        return {
            "client.ts": _generate_client(spec),
            "models.ts": _generate_models(schemas),
        }
