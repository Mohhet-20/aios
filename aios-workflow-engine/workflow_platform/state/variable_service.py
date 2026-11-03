"""VariableService: persistent, longer-lived state — `VariableModel` rows
scoped to `workflow | execution | workspace | global` — orthogonal to
`ExecutionModel.context_variables`, which is ephemeral, single-run state
the Execution Engine reads/writes directly as it walks a graph (see
`domain/enums.py`'s module docstring for the full rationale). A workflow
author reaches for a persistent Variable when a value needs to outlive
one run (an API key every execution of this workflow should see, a
running total across every invocation of a recurring schedule); they
reach for `context_variables` when a value is just this run's working
state.

`is_secret=True` variables are encrypted at rest (see
`security/encryption.py`) and — deliberately — excluded from
`resolve_scope_chain`/`resolve_template`'s merged view unless the caller
passes `include_secrets=True`. Template output routinely ends up in
`context_variables`, checkpoints, and execution logs, all of which are
broadly readable; a secret should only ever surface where a call site
specifically asked for it (e.g. a REST_API node handler building an
Authorization header), not by accident because it happened to share a
key name with something a template referenced. `get_variable` (an
explicit, single-name lookup) always returns the real decrypted value —
the leakage risk is specifically about secrets being swept up into a
*merge* the caller didn't ask for by name.

`resolve_template` does simple `{{key}}` substitution against a merged
view of every scope in precedence order (execution beats workflow beats
workspace beats global) plus an optional `extra` dict (typically the
execution's own `context_variables`, given the highest precedence of
all) — the same lookup a REST_API node's URL or an LLM_CALL node's
prompt config would want before this platform even considers a real
templating engine (Jinja2, etc.) worth the dependency."""
from __future__ import annotations

import json
import re

from workflow_platform.core.exceptions import ValidationError, VariableResolutionError
from workflow_platform.domain.enums import VariableScope
from workflow_platform.models.variable import VariableModel
from workflow_platform.repositories.registry import RepositoryRegistry
from workflow_platform.security.encryption import SecretsEncryptor, get_default_encryptor

_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

# execution beats workflow beats workspace beats global — most-specific-wins,
# read in this order so a later (more general) scope never overwrites an
# earlier (more specific) one when merging.
_SCOPE_PRECEDENCE = [VariableScope.EXECUTION, VariableScope.WORKFLOW, VariableScope.WORKSPACE, VariableScope.GLOBAL]


class VariableService:
    def __init__(self, repos: RepositoryRegistry, *, encryptor: SecretsEncryptor | None = None):
        self.repos = repos
        self._encryptor = encryptor or get_default_encryptor()

    def _encode(self, value, *, is_secret: bool) -> dict:
        if not is_secret:
            return {"v": value}
        return {"v": self._encryptor.encrypt(json.dumps(value))}

    def _decode(self, model: VariableModel):
        if not model.is_secret:
            return model.value.get("v")
        return json.loads(self._encryptor.decrypt(model.value["v"]))

    async def set_variable(self, scope_type: VariableScope | str, scope_id: str, key: str, value, *, is_secret: bool = False) -> VariableModel:
        scope_type = VariableScope(scope_type).value
        encoded = self._encode(value, is_secret=is_secret)
        existing = await self.repos.variables.get_by_key(scope_type, scope_id, key)
        if existing is not None:
            existing.value = encoded
            existing.is_secret = is_secret
            return await self.repos.variables.update(existing)
        return await self.repos.variables.add(VariableModel(
            scope_type=scope_type, scope_id=scope_id, key=key, value=encoded, is_secret=is_secret,
        ))

    async def get_variable(self, scope_type: VariableScope | str, scope_id: str, key: str, *, default=None):
        scope_type = VariableScope(scope_type).value
        model = await self.repos.variables.get_by_key(scope_type, scope_id, key)
        if model is None:
            return default
        return self._decode(model)

    async def delete_variable(self, scope_type: VariableScope | str, scope_id: str, key: str) -> bool:
        scope_type = VariableScope(scope_type).value
        model = await self.repos.variables.get_by_key(scope_type, scope_id, key)
        if model is None:
            return False
        await self.repos.variables.delete(model, hard=True)
        return True

    async def list_for_scope(self, scope_type: VariableScope | str, scope_id: str) -> list[VariableModel]:
        return await self.repos.variables.list_for_scope(VariableScope(scope_type).value, scope_id)

    # -- multi-scope merge + templating -------------------------------------------

    async def resolve_scope_chain(
        self, *, execution_id: str | None = None, workflow_id: str | None = None,
        workspace_id: str | None = None, global_scope_id: str = "global", include_secrets: bool = False,
    ) -> dict:
        """Merges every applicable scope into one flat dict, most-specific
        scope winning on key collisions. Secrets are excluded unless
        `include_secrets=True` — see the module docstring."""
        scope_ids = {
            VariableScope.EXECUTION: execution_id, VariableScope.WORKFLOW: workflow_id,
            VariableScope.WORKSPACE: workspace_id, VariableScope.GLOBAL: global_scope_id,
        }
        merged: dict = {}
        # iterate least-specific first so more-specific scopes overwrite on collision
        for scope in reversed(_SCOPE_PRECEDENCE):
            scope_id = scope_ids.get(scope)
            if not scope_id:
                continue
            for model in await self.list_for_scope(scope, scope_id):
                if model.is_secret and not include_secrets:
                    continue
                merged[model.key] = self._decode(model)
        return merged

    async def resolve_template(
        self, text: str, *, execution_id: str | None = None, workflow_id: str | None = None,
        workspace_id: str | None = None, extra: dict | None = None, include_secrets: bool = False,
    ) -> str:
        if not isinstance(text, str):
            raise ValidationError("resolve_template requires a string")
        merged = await self.resolve_scope_chain(
            execution_id=execution_id, workflow_id=workflow_id, workspace_id=workspace_id, include_secrets=include_secrets,
        )
        merged.update(extra or {})  # execution's own live context_variables take precedence over everything

        def _substitute(match: re.Match) -> str:
            key = match.group(1)
            if key not in merged:
                raise VariableResolutionError(f"unresolved variable '{{{{{key}}}}}' — not found in any scope")
            return str(merged[key])

        return _TEMPLATE_PATTERN.sub(_substitute, text)
