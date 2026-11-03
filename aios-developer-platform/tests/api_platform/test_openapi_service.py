from developer_platform.api_platform.openapi_service import OpenApiSpecService, RouteDescriptor
from developer_platform.models.api_platform import ApiVersionModel


def test_build_spec_produces_valid_shape():
    service = OpenApiSpecService()
    routes = [
        RouteDescriptor(
            path="/v1/api-keys", method="POST", operation_id="issue_api_key",
            summary="Issue an API key", tags=["api-platform"],
            request_schema={"type": "object"}, response_schema={"type": "object"},
        ),
        RouteDescriptor(path="/v1/api-keys", method="GET", operation_id="list_api_keys", tags=["api-platform"]),
    ]
    spec = service.build_spec(title="Developer Platform API", version="v1", description="test", routes=routes)

    assert spec["openapi"] == "3.0.3"
    assert spec["info"]["title"] == "Developer Platform API"
    assert "post" in spec["paths"]["/v1/api-keys"]
    assert "get" in spec["paths"]["/v1/api-keys"]
    assert spec["paths"]["/v1/api-keys"]["post"]["requestBody"]["required"] is True


def test_annotate_with_versions():
    service = OpenApiSpecService()
    spec = service.build_spec(title="t", version="v1")
    versions = [ApiVersionModel(version="v1", status="active", notes=None)]
    annotated = service.annotate_with_versions(spec, versions)
    assert annotated["x-api-versions"][0]["version"] == "v1"
    assert "x-api-versions" not in spec
