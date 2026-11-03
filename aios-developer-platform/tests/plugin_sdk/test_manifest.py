from developer_platform.plugin_sdk.manifest import scaffold_manifest, validate_manifest


def test_valid_manifest_has_no_errors():
    manifest = scaffold_manifest(name="my-tool", category="tool")
    manifest["permissions"] = ["network.outbound"]
    errors = validate_manifest(manifest)
    assert errors == []


def test_missing_required_fields_reported():
    errors = validate_manifest({})
    assert any("name" in e for e in errors)
    assert any("entrypoint" in e for e in errors)


def test_invalid_category_reported():
    manifest = scaffold_manifest(name="x", category="not-a-real-category")
    errors = validate_manifest(manifest)
    assert any("category" in e for e in errors)


def test_unknown_permission_reported():
    manifest = scaffold_manifest(name="x", category="tool")
    manifest["permissions"] = ["do-anything"]
    errors = validate_manifest(manifest)
    assert any("unknown permission" in e for e in errors)


def test_scaffold_manifest_defaults():
    manifest = scaffold_manifest(name="widget", category="dashboard")
    assert manifest["name"] == "widget"
    assert manifest["category"] == "dashboard"
    assert manifest["entrypoint"] == "main.py"
    assert manifest["version"] == "0.1.0"
