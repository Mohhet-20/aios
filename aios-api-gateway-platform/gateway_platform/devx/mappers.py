from __future__ import annotations

from gateway_platform.domain.entities import SdkGenJob
from gateway_platform.domain.enums import SdkGenStatus
from gateway_platform.models.devx import SdkGenJobModel


def sdk_gen_job_to_domain(model: SdkGenJobModel) -> SdkGenJob:
    return SdkGenJob(id=model.id, status=SdkGenStatus(model.status))


def apply_sdk_gen_job_domain_to_model(entity: SdkGenJob, model: SdkGenJobModel) -> None:
    model.status = entity.status.value
