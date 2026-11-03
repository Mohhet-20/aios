"""SDK / client code generation: a guarded queued -> running ->
completed/failed job lifecycle wrapping generation of a real,
`ast`-validated Python HTTP client from an OpenAPI-shaped spec --
the same disclosed boundary the Developer Platform's `codegen`
module drew: Python output is genuinely syntax-validated, other
languages get a structural sanity check (every path must appear
somewhere in the generated source) since this platform doesn't ship
a TypeScript/Java/Go compiler to validate against."""
from __future__ import annotations

import ast

from gateway_platform.core.exceptions import SdkGenerationFailedError, ValidationError
from gateway_platform.devx.mappers import apply_sdk_gen_job_domain_to_model, sdk_gen_job_to_domain
from gateway_platform.domain.enums import CodeGenLanguage
from gateway_platform.models.devx import SdkGenJobModel
from gateway_platform.repositories.registry import RepositoryRegistry


def _operation_id(method: str, path: str) -> str:
    slug = "".join(ch if ch.isalnum() else "_" for ch in path).strip("_")
    return f"{method.lower()}_{slug}"


def _render_python_client(spec: dict) -> str:
    lines = [
        "from __future__ import annotations",
        "",
        "import httpx",
        "",
        "",
        "class GatewayClient:",
        "    def __init__(self, base_url: str, api_key: str | None = None):",
        "        self.base_url = base_url",
        "        self.api_key = api_key",
        "",
    ]
    paths = spec.get("paths", {})
    if not paths:
        lines.append("    pass")
    for path, operations in paths.items():
        for method in operations:
            method_name = _operation_id(method, path)
            lines.append(f"    def {method_name}(self, **kwargs):")
            lines.append(
                f'        return httpx.request("{method.upper()}", f"{{self.base_url}}{path}", **kwargs)'
            )
            lines.append("")
    return "\n".join(lines) + "\n"


def _render_typescript_client(spec: dict) -> str:
    lines = ["export class GatewayClient {", "  constructor(private baseUrl: string, private apiKey?: string) {}", ""]
    for path, operations in spec.get("paths", {}).items():
        for method in operations:
            method_name = _operation_id(method, path)
            lines.append(f"  async {method_name}(init?: RequestInit) {{")
            lines.append(f"    return fetch(`${{this.baseUrl}}{path}`, {{ ...init, method: \"{method.upper()}\" }});")
            lines.append("  }")
            lines.append("")
    lines.append("}")
    return "\n".join(lines) + "\n"


_RENDERERS = {
    CodeGenLanguage.PYTHON.value: _render_python_client,
    CodeGenLanguage.TYPESCRIPT.value: _render_typescript_client,
}


class SdkCodeGenService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_job(self, tenant_id: str, *, language: str, api_version: str) -> SdkGenJobModel:
        try:
            CodeGenLanguage(language)
        except ValueError as exc:
            raise ValidationError(f"'{language}' is not a supported code generation language") from exc
        job = SdkGenJobModel(tenant_id=tenant_id, language=language, api_version=api_version, status="queued")
        return await self.repos.sdk_gen_jobs.add(job)

    async def run_job(self, tenant_id: str, job_id: str, *, spec: dict) -> SdkGenJobModel:
        """Runs generation synchronously end-to-end: queued -> running
        -> completed (artifact_ref holds the generated source) or
        failed (error holds the reason)."""
        job = await self._get_or_404(tenant_id, job_id)
        entity = sdk_gen_job_to_domain(job)
        entity.start()
        apply_sdk_gen_job_domain_to_model(entity, job)
        job = await self.repos.sdk_gen_jobs.update(job)

        renderer = _RENDERERS.get(job.language)
        if renderer is None:
            return await self._fail(tenant_id, job, f"no renderer registered for language '{job.language}'")

        source = renderer(spec)
        if job.language == CodeGenLanguage.PYTHON.value:
            try:
                ast.parse(source)
            except SyntaxError as exc:
                return await self._fail(tenant_id, job, f"generated Python failed ast.parse: {exc}")
        else:
            for path in spec.get("paths", {}):
                if path not in source:
                    return await self._fail(tenant_id, job, f"generated source missing expected path '{path}'")

        entity = sdk_gen_job_to_domain(job)
        entity.complete()
        apply_sdk_gen_job_domain_to_model(entity, job)
        job.artifact_ref = source
        return await self.repos.sdk_gen_jobs.update(job)

    async def _fail(self, tenant_id: str, job: SdkGenJobModel, reason: str) -> SdkGenJobModel:
        entity = sdk_gen_job_to_domain(job)
        entity.fail()
        apply_sdk_gen_job_domain_to_model(entity, job)
        job.error = reason
        job = await self.repos.sdk_gen_jobs.update(job)
        raise SdkGenerationFailedError(reason)

    async def list_for_tenant(self, tenant_id: str) -> list[SdkGenJobModel]:
        return await self.repos.sdk_gen_jobs.list_for_tenant(tenant_id)

    async def _get_or_404(self, tenant_id: str, job_id: str) -> SdkGenJobModel:
        job = await self.repos.sdk_gen_jobs.get_or_404(job_id)
        if job.tenant_id != tenant_id:
            raise SdkGenerationFailedError(f"job '{job_id}' not found for tenant '{tenant_id}'")
        return job
