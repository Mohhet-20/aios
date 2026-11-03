from developer_platform.codegen.generators.typescript_generator import TypeScriptClientGenerator

SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "Dev Platform API", "version": "v1"},
    "paths": {
        "/v1/plugins": {
            "get": {"operationId": "list_plugins", "summary": "List plugins", "responses": {}},
        },
    },
    "components": {
        "schemas": {
            "Plugin": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "install_count": {"type": "integer"}},
                "required": ["id"],
            }
        }
    },
}


def test_generates_client_and_models_files():
    files = TypeScriptClientGenerator().generate(SPEC)
    assert set(files) == {"client.ts", "models.ts"}
    assert "export class GeneratedClient" in files["client.ts"]
    assert "list_plugins" in files["client.ts"]


def test_models_use_optional_marker_for_non_required_fields():
    files = TypeScriptClientGenerator().generate(SPEC)
    assert "export interface Plugin {" in files["models.ts"]
    assert "id: string;" in files["models.ts"]
    assert "install_count?: number;" in files["models.ts"]


def test_empty_schemas_produce_valid_shape():
    files = TypeScriptClientGenerator().generate({"info": {}, "paths": {}})
    assert "export class GeneratedClient" in files["client.ts"]
    assert files["models.ts"].strip().startswith("//")
