"""ORM <-> domain-aggregate bridge for `CodeGenJob`."""
from __future__ import annotations

from developer_platform.domain.entities import CodeGenJob
from developer_platform.domain.enums import CodeGenStatus
from developer_platform.models.codegen import CodeGenJobModel


def codegen_job_to_domain(model: CodeGenJobModel) -> CodeGenJob:
    return CodeGenJob(id=model.id, status=CodeGenStatus(model.status), finished_at=model.finished_at)


def apply_codegen_job_domain_to_model(entity: CodeGenJob, model: CodeGenJobModel) -> None:
    model.status = entity.status.value
    model.finished_at = entity.finished_at
