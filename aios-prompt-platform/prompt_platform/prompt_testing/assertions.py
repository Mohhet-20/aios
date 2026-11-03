"""Assertion evaluators for prompt testing. Each returns (passed: bool,
reason: str | None) so a failing assertion always carries a human-readable
explanation into the TestResult."""
from __future__ import annotations

import re

from ai_core.structured_output.parser import parse_json_response
from ai_core.utils.exceptions import StructuredOutputError

try:
    import jsonschema
except ImportError:  # pragma: no cover — jsonschema ships via ai_core's own deps
    jsonschema = None

from prompt_platform.domain.enums import AssertionType


def evaluate_assertion(assertion: dict, response_text: str) -> tuple[bool, str | None]:
    assertion_type = AssertionType(assertion["type"])
    value = assertion.get("value")

    if assertion_type == AssertionType.EXACT:
        passed = response_text.strip() == str(value).strip()
        return passed, None if passed else f"expected exact match {value!r}, got {response_text!r}"

    if assertion_type == AssertionType.CONTAINS:
        passed = str(value) in response_text
        return passed, None if passed else f"expected response to contain {value!r}"

    if assertion_type == AssertionType.NOT_CONTAINS:
        passed = str(value) not in response_text
        return passed, None if passed else f"expected response to NOT contain {value!r}"

    if assertion_type == AssertionType.REGEX:
        passed = re.search(str(value), response_text) is not None
        return passed, None if passed else f"expected response to match regex {value!r}"

    if assertion_type == AssertionType.JSON_SCHEMA:
        try:
            parsed = parse_json_response(response_text)
        except StructuredOutputError as exc:
            return False, f"response is not valid JSON: {exc}"
        if jsonschema is None:
            return False, "jsonschema package not available to validate JSON_SCHEMA assertion"
        try:
            jsonschema.validate(instance=parsed, schema=value)
            return True, None
        except jsonschema.ValidationError as exc:
            return False, f"response JSON failed schema validation: {exc.message}"

    return False, f"unknown assertion type {assertion_type}"


def evaluate_all(assertions: list[dict], response_text: str) -> list[str]:
    """Returns the list of failure reasons (empty list = all passed)."""
    failures = []
    for assertion in assertions:
        passed, reason = evaluate_assertion(assertion, response_text)
        if not passed:
            failures.append(reason or "assertion failed")
    return failures
