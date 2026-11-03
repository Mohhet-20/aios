import ast

from developer_platform.codegen.generators.python_generator import PythonClientGenerator

SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "Dev Platform API", "version": "v1"},
    "paths": {
        "/v1/api-keys": {
            "post": {"operationId": "issue_api_key", "summary": "Issue a key", "responses": {}},
            "get": {"operationId": "list_api_keys", "responses": {}},
        },
    },
    "components": {
        "schemas": {
            "ApiKey": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"}, "name": {"type": "string"},
                    "rate_limit_per_minute": {"type": "integer"},
                },
                "required": ["id", "name"],
            }
        }
    },
}


def test_generates_valid_python_client():
    files = PythonClientGenerator().generate(SPEC)
    assert set(files) == {"client.py", "models.py"}
    ast.parse(files["client.py"])
    ast.parse(files["models.py"])


def test_client_has_one_method_per_operation():
    files = PythonClientGenerator().generate(SPEC)
    assert "def issue_api_key(self" in files["client.py"]
    assert "def list_api_keys(self" in files["client.py"]


def test_models_reflect_required_and_optional_fields():
    files = PythonClientGenerator().generate(SPEC)
    assert "id: str" in files["models.py"]
    assert "name: str" in files["models.py"]
    assert "rate_limit_per_minute: int | None = None" in files["models.py"]


def test_empty_schemas_produce_valid_empty_models_file():
    files = PythonClientGenerator().generate({"info": {}, "paths": {}})
    ast.parse(files["models.py"])
    ast.parse(files["client.py"])
