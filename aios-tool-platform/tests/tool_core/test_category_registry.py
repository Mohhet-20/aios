from tool_platform.domain.enums import ToolCategory
from tool_platform.tool_registry.registry import CATEGORY_SPECS, get_category_spec


def test_every_category_enum_value_has_a_spec():
    assert {s.key for s in CATEGORY_SPECS} == {c.value for c in ToolCategory}


def test_get_category_spec_known_and_unknown():
    assert get_category_spec("github").connector_key == "github"
    assert get_category_spec("not-a-real-category") is None


def test_sandboxed_categories_are_marked():
    sandboxed_keys = {s.key for s in CATEGORY_SPECS if s.sandboxed_by_default}
    assert {"python_execution", "shell_command", "file_manager"} <= sandboxed_keys
