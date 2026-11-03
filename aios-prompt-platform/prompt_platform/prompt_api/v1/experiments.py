"""Prompt Experiments: A/B and multi-variant testing, statistical
summaries, winner selection."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from prompt_platform.domain.enums import EvalMetric
from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_experiment_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_experiments.experiment_service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["experiments"])


class CreateExperimentRequest(BaseModel):
    workspace_id: str
    prompt_id: str
    name: str
    description: str | None = None
    hypothesis: str | None = None
    sample_size_per_variant: int = 10
    random_seed: int = 42


class AddVariantRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    prompt_version_id: str | None = None
    model_override: str | None = None
    provider_override: str | None = None
    temperature_override: float | None = None
    parameter_overrides: dict = {}
    traffic_percent: float = 50.0


class RunExperimentRequest(BaseModel):
    test_inputs: list[dict]
    metric: EvalMetric = EvalMetric.ACCURACY


@router.post("", status_code=201)
async def create_experiment(body: CreateExperimentRequest, actor_id: str = Depends(get_current_actor_id), svc: ExperimentService = Depends(get_experiment_service)):
    experiment = await svc.create_experiment(
        body.workspace_id, body.prompt_id, name=body.name, actor_id=actor_id, description=body.description,
        hypothesis=body.hypothesis, sample_size_per_variant=body.sample_size_per_variant, random_seed=body.random_seed,
    )
    return to_dict(experiment)


@router.get("")
async def list_experiments(workspace_id: str, svc: ExperimentService = Depends(get_experiment_service)):
    return to_dict_list(await svc.list_experiments(workspace_id))


@router.post("/{experiment_id}/variants", status_code=201)
async def add_variant(experiment_id: str, body: AddVariantRequest, svc: ExperimentService = Depends(get_experiment_service)):
    variant = await svc.add_variant(
        experiment_id, name=body.name, prompt_version_id=body.prompt_version_id, model_override=body.model_override,
        provider_override=body.provider_override, temperature_override=body.temperature_override,
        parameter_overrides=body.parameter_overrides, traffic_percent=body.traffic_percent,
    )
    return to_dict(variant)


@router.get("/{experiment_id}/variants")
async def list_variants(experiment_id: str, svc: ExperimentService = Depends(get_experiment_service)):
    return to_dict_list(await svc.list_variants(experiment_id))


@router.post("/{experiment_id}/start")
async def start_experiment(experiment_id: str, svc: ExperimentService = Depends(get_experiment_service)):
    return to_dict(await svc.start_experiment(experiment_id))


@router.post("/{experiment_id}/run")
async def run_experiment(experiment_id: str, body: RunExperimentRequest, actor_id: str = Depends(get_current_actor_id), svc: ExperimentService = Depends(get_experiment_service)):
    experiment = await svc.run(experiment_id, test_inputs=body.test_inputs, metric=body.metric, triggered_by=actor_id)
    return to_dict(experiment)


@router.get("/{experiment_id}/results")
async def get_results(experiment_id: str, svc: ExperimentService = Depends(get_experiment_service)):
    return to_dict_list(await svc.get_results(experiment_id))


@router.get("/{experiment_id}/statistical-summary")
async def statistical_summary(experiment_id: str, metric: EvalMetric = EvalMetric.ACCURACY, svc: ExperimentService = Depends(get_experiment_service)):
    return await svc.statistical_summary(experiment_id, metric=metric)


@router.post("/{experiment_id}/archive")
async def archive_experiment(experiment_id: str, svc: ExperimentService = Depends(get_experiment_service)):
    return to_dict(await svc.archive(experiment_id))
