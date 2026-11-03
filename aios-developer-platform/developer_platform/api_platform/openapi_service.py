"""OpenAPI spec generation hooks. This platform's real FastAPI app
(built in a later task) generates its own spec via `app.openapi()`;
this service is the seam other modules use *before* that app exists —
the Code Generation Engine builds SDK/client stubs from exactly this
shape of document, and the Developer Portal's API explorer renders
whatever spec is handed to it. `build_spec` assembles a real, valid
minimal OpenAPI 3.0 document from a declarative list of routes rather
than a hand-maintained string template, so a generator can walk it
programmatically."""
from __future__ import annotations

from dataclasses import dataclass, field

from developer_platform.models.api_platform import ApiVersionModel


@dataclass
class RouteDescriptor:
    path: str
    method: str
    operation_id: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    request_schema: dict | None = None
    response_schema: dict | None = None


class OpenApiSpecService:
    def build_spec(
        self, *, title: str, version: str, description: str = "", routes: list[RouteDescriptor] | None = None,
        schemas: dict[str, dict] | None = None,
    ) -> dict:
        paths: dict[str, dict] = {}
        for route in routes or []:
            operation: dict = {
                "operationId": route.operation_id,
                "summary": route.summary,
                "tags": route.tags,
                "responses": {
                    "200": {
                        "description": "Successful response",
                        **(
                            {"content": {"application/json": {"schema": route.response_schema}}}
                            if route.response_schema
                            else {}
                        ),
                    }
                },
            }
            if route.request_schema is not None:
                operation["requestBody"] = {
                    "required": True,
                    "content": {"application/json": {"schema": route.request_schema}},
                }
            paths.setdefault(route.path, {})[route.method.lower()] = operation

        spec: dict = {
            "openapi": "3.0.3",
            "info": {"title": title, "version": version, "description": description},
            "paths": paths,
        }
        if schemas:
            spec["components"] = {"schemas": schemas}
        return spec

    def annotate_with_versions(self, spec: dict, versions: list[ApiVersionModel]) -> dict:
        """Attaches a non-standard `x-api-versions` extension listing
        every registered API version and its lifecycle status — a
        generator or the Developer Portal can surface this without
        needing a separate round trip to the API Platform's version
        endpoint."""
        spec = dict(spec)
        spec["x-api-versions"] = [
            {"version": v.version, "status": v.status, "deprecated_at": v.deprecated_at, "sunset_at": v.sunset_at}
            for v in versions
        ]
        return spec
