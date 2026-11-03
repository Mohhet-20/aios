"""Prompt Studio validation: catches malformed templates, undeclared/
unused variables, and oversized prompts before a draft is saved. Reuses
`ai_core.prompts.template.PromptTemplate`'s public `required_variables`
extraction (the exact `{{variable}}` convention every model call in AIOS
renders against) rather than re-implementing placeholder parsing here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.enums import Role

from prompt_platform.core.exceptions import ValidationError


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    field: str
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _used_variables(text: str | None, role: Role) -> set[str]:
    if not text:
        return set()
    return PromptTemplate(name="_scratch", role=role, template=text).required_variables


def validate_draft(
    *,
    system_template: str | None,
    developer_template: str | None,
    user_template: str,
    variables_schema: list[dict],
    parameters: dict,
    max_chars: int,
) -> ValidationReport:
    report = ValidationReport()

    if not user_template or not user_template.strip():
        report.issues.append(ValidationIssue("error", "user_template", "user_template must not be empty"))

    total_chars = len(user_template or "") + len(system_template or "") + len(developer_template or "")
    if total_chars > max_chars:
        report.issues.append(
            ValidationIssue("error", "template", f"combined template length {total_chars} exceeds the {max_chars}-char limit")
        )

    declared_names = [v.get("name") for v in variables_schema]
    if len(declared_names) != len(set(declared_names)):
        report.issues.append(ValidationIssue("error", "variables_schema", "duplicate variable names declared"))
    for v in variables_schema:
        if not v.get("name"):
            report.issues.append(ValidationIssue("error", "variables_schema", "every variable must have a 'name'"))

    used = (
        _used_variables(system_template, Role.SYSTEM)
        | _used_variables(developer_template, Role.DEVELOPER)
        | _used_variables(user_template, Role.USER)
    )
    declared = {n for n in declared_names if n}

    for undeclared in used - declared:
        report.issues.append(
            ValidationIssue("error", "variables_schema", f"template references undeclared variable '{{{{{undeclared}}}}}'")
        )
    for unused in declared - used:
        report.issues.append(
            ValidationIssue("warning", "variables_schema", f"variable '{unused}' is declared but never used in any template")
        )

    temperature = parameters.get("temperature")
    if temperature is not None and not (0 <= temperature <= 2):
        report.issues.append(ValidationIssue("error", "parameters.temperature", f"temperature {temperature} must be within [0, 2]"))

    return report


def validate_draft_or_raise(**kwargs) -> ValidationReport:
    report = validate_draft(**kwargs)
    if not report.is_valid:
        messages = "; ".join(f"{i.field}: {i.message}" for i in report.errors)
        raise ValidationError(f"prompt draft failed validation: {messages}")
    return report
