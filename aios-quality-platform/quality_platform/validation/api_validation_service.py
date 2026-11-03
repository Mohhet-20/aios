"""API validation: schema/request/response/contract/backward/version/
SDK compatibility checks. These are synchronous pass/fail checks, not
long-running jobs (no queued/running/completed/failed lifecycle) --
`run_validation` records its outcome immediately, the same "check now,
record the result" shape used across every prior AIOS platform for
genuinely instantaneous validations."""
from __future__ import annotations

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import UnsupportedApiValidationTypeError
from quality_platform.domain.enums import ValidationOutcome
from quality_platform.models.validation import ApiValidationRunModel
from quality_platform.repositories.registry import RepositoryRegistry


class ApiValidationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def run_validation(
        self, tenant_id: str, *, validation_type: str, target_ref: str, errors: list[str] | None = None
    ) -> ApiValidationRunModel:
        if validation_type not in self.settings.api_validation_types:
            raise UnsupportedApiValidationTypeError(f"Unsupported API validation type '{validation_type}'")
        errors = errors or []
        outcome = ValidationOutcome.FAILED if errors else ValidationOutcome.PASSED
        run = ApiValidationRunModel(
            tenant_id=tenant_id, validation_type=validation_type, target_ref=target_ref,
            outcome=outcome.value, details={"errors": errors},
        )
        return await self.repos.api_validation_runs.add(run)

    async def list_runs(self, tenant_id: str, *, validation_type: str | None = None, limit: int = 100) -> list[ApiValidationRunModel]:
        return await self.repos.api_validation_runs.list_for_tenant(tenant_id, validation_type=validation_type, limit=limit)
