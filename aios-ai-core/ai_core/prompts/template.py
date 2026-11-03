"""Prompt templating. Deliberately NOT Jinja2 — a single regex-based
`{{variable}}` substitution is enough for system/user/developer prompt text
and carries no template-language attack surface (no arbitrary expression
evaluation, no filters that could be abused). If a future need for loops/
conditionals in templates arises, that's a deliberate, reviewed dependency
addition, not something that should sneak in via a generic templating lib.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from ai_core.schemas.enums import Role
from ai_core.utils.exceptions import PromptValidationError

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _extract_variables(template: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(template))


def _substitute(template: str, variables: dict) -> str:
    def _replace(match: re.Match) -> str:
        return str(variables[match.group(1)])

    return _PLACEHOLDER_RE.sub(_replace, template)


@dataclass
class PromptTemplate:
    name: str
    role: Role
    template: str
    version: int = 1
    required_variables: set[str] | None = None
    preprocess: Callable[[dict], dict] | None = None

    def __post_init__(self) -> None:
        if self.required_variables is None:
            self.required_variables = _extract_variables(self.template)

    def render(self, variables: dict | None = None) -> str:
        variables = dict(variables or {})
        if self.preprocess is not None:
            variables = self.preprocess(variables)
        missing = self.required_variables - variables.keys()
        if missing:
            raise PromptValidationError(
                f"prompt template '{self.name}' (v{self.version}) is missing required variables: {sorted(missing)}"
            )
        rendered = _substitute(self.template, variables)
        leftover = _extract_variables(rendered)
        if leftover:
            raise PromptValidationError(
                f"prompt template '{self.name}' (v{self.version}) rendered with unfilled placeholders: {sorted(leftover)}"
            )
        return rendered
