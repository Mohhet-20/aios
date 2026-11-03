"""Azure OpenAI adapter. Reuses all of OpenAICompatibleProvider's payload
serialization and response parsing — Azure speaks the same JSON shapes as
OpenAI itself — but the URL is deployment-scoped and auth uses an
`api-key` header instead of `Authorization: Bearer`. `model` is treated as
the Azure *deployment name* throughout, since that's what Azure actually
routes on.
"""
from __future__ import annotations

from typing import Any

from ai_core.providers.openai_compatible import OpenAICompatibleProvider


class AzureOpenAIProvider(OpenAICompatibleProvider):
    provider_name = "azure_openai"

    def __init__(self, *, api_key: str = "", endpoint: str = "", api_version: str = "2024-06-01", **kwargs: Any):
        super().__init__(api_key=api_key, base_url=endpoint.rstrip("/"), **kwargs)
        self.api_version = api_version

    def _build_url(self, path: str, *, model: str | None = None) -> str:
        deployment = model or "default"
        return f"{self.base_url}/openai/deployments/{deployment}{path}?api-version={self.api_version}"

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["api-key"] = self.api_key
        return headers
