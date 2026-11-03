"""API testing console ("try it out"): fires a request through an
injectable `sender` callable and records the exchange for later
inspection. `sender` mirrors the webhook delivery module's seam --
tests pass a trivial stand-in, production wires in a real HTTP call
-- kept separate from the webhook module's `Sender` type since this
one deals in status codes plus a JSON body, not a signed delivery
envelope."""
from __future__ import annotations

from collections.abc import Callable

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import TestConsoleRequestFailedError
from gateway_platform.models.devx import TestConsoleRequestModel
from gateway_platform.repositories.registry import RepositoryRegistry

ConsoleSenderResult = tuple[int, dict]
ConsoleSender = Callable[[dict], ConsoleSenderResult]


def _default_sender(request_payload: dict) -> ConsoleSenderResult:
    return 200, {"echo": request_payload}


class TestingConsoleService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def execute(
        self, tenant_id: str, route_id: str, *, request_payload: dict, sender: ConsoleSender | None = None,
    ) -> TestConsoleRequestModel:
        sender = sender or _default_sender
        try:
            status_code, response_payload = sender(request_payload)
        except Exception as exc:
            raise TestConsoleRequestFailedError(f"test console request failed: {exc}") from exc

        record = TestConsoleRequestModel(
            tenant_id=tenant_id, route_id=route_id, request_payload=request_payload,
            response_payload=response_payload, status_code=status_code,
        )
        return await self.repos.test_console_requests.add(record)

    async def list_for_route(self, tenant_id: str, route_id: str, *, limit: int = 100) -> list[TestConsoleRequestModel]:
        return await self.repos.test_console_requests.list_for_route(tenant_id, route_id, limit=limit)
