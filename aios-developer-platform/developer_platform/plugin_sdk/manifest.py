"""Plugin manifest validation + starter templates. The manifest is a
plain JSON object stored on `PluginVersionModel.manifest`; validation
here is deliberately structural (required fields present, category and
permissions well-formed, entrypoint referenced) rather than executing
any plugin code — this platform is a control plane for plugin
metadata and lifecycle, not a code sandbox (that concern already
lives in the Tool Platform's sandbox/execution engine and is not
duplicated here)."""
from __future__ import annotations

from developer_platform.domain.enums import ExtensionCategory

REQUIRED_MANIFEST_FIELDS = ("name", "version", "entrypoint", "category", "permissions")
ALLOWED_PERMISSIONS = frozenset({
    "network.outbound", "filesystem.read", "filesystem.write", "secrets.read",
    "memory.read", "memory.write", "tools.invoke", "workflows.trigger", "dashboards.render",
})


def validate_manifest(manifest: dict) -> list[str]:
    """Returns a list of validation error strings — empty means valid.
    Never raises; callers decide what to do with a non-empty list
    (the lifecycle service persists it to `validation_errors` either
    way, so a rejected submission keeps a durable record of why)."""
    errors: list[str] = []

    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest or manifest.get(field) in (None, ""):
            errors.append(f"missing required field '{field}'")

    category = manifest.get("category")
    if category is not None:
        valid_categories = {c.value for c in ExtensionCategory}
        if category not in valid_categories:
            errors.append(f"category '{category}' is not one of {sorted(valid_categories)}")

    permissions = manifest.get("permissions")
    if permissions is not None:
        if not isinstance(permissions, list):
            errors.append("'permissions' must be a list")
        else:
            unknown = sorted(set(permissions) - ALLOWED_PERMISSIONS)
            if unknown:
                errors.append(f"unknown permission(s): {unknown}")

    entrypoint = manifest.get("entrypoint")
    if entrypoint is not None and not isinstance(entrypoint, str):
        errors.append("'entrypoint' must be a string path")

    dependencies = manifest.get("dependencies", [])
    if not isinstance(dependencies, list):
        errors.append("'dependencies' must be a list")

    return errors


def scaffold_manifest(*, name: str, category: str, version: str = "0.1.0", entrypoint: str | None = None) -> dict:
    """Generates a starter manifest for `aios plugin init` / the
    Developer Portal's "new plugin" flow — one template shape reused
    across every category rather than eleven near-identical hand-authored
    templates, parameterized by category."""
    return {
        "name": name,
        "version": version,
        "category": category,
        "entrypoint": entrypoint or "main.py",
        "permissions": [],
        "dependencies": [],
        "description": f"A new {category} plugin scaffolded from the AIOS Plugin SDK template.",
    }
