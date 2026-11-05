"""All twenty AIOS services in one process, for the hosted public demo (deploy/demo/Dockerfile).

Each service stays an unmodified FastAPI application; this module only imports them and dispatches
``/svc/<name>/...`` to the matching one with the prefix stripped, so every service sees exactly the paths (and
health-probe exemptions) it sees when it runs on its own port. Their own lifespans run, so each creates and
migrates its own SQLite database (distinct default file names, all under the working directory).

One process instead of twenty is what lets the platform fit a 512 MB free instance: the interpreter and the shared
libraries are loaded once. The microservice boundaries are unchanged (separate databases, the X-Internal-Token
guard on every service, no imports across services except the AI Core library, as in the real deployment).
"""
from __future__ import annotations

import importlib
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# URL name the console uses (lib/server/config.ts) -> (service directory, import target, is factory).
SERVICES: dict[str, tuple[str, str, bool]] = {
    "backend": ("aios-backend", "app.main:app", False),
    "ai-core": ("aios-ai-core", "ai_core.main:app", False),
    "prompt": ("aios-prompt-platform", "prompt_platform.main:app", False),
    "agent": ("aios-agent-platform", "agent_platform.main:app", False),
    "memory": ("aios-memory-platform", "memory_platform.main:app", False),
    "workflow": ("aios-workflow-engine", "workflow_platform.workflow_api.application_factory:create_app", True),
    "tool": ("aios-tool-platform", "tool_platform.tool_api.application_factory:create_app", True),
    "evaluation": ("aios-evaluation-platform", "eval_platform.eval_api.application_factory:create_app", True),
    "identity": ("aios-identity-platform", "identity_platform.identity_api.application_factory:create_app", True),
    "collaboration": ("aios-collaboration-platform", "collaboration_platform.collab_api.application_factory:create_app", True),
    "observability": ("aios-observability-platform", "observability_platform.obs_api.application_factory:create_app", True),
    "security": ("aios-security-platform", "security_platform.sec_api.application_factory:create_app", True),
    "infrastructure": ("aios-infrastructure-platform", "infra_platform.infra_api.application_factory:create_app", True),
    "developer": ("aios-developer-platform", "developer_platform.dev_api.application_factory:create_app", True),
    "gateway": ("aios-api-gateway-platform", "gateway_platform.gw_api.application_factory:create_app", True),
    "analytics": ("aios-analytics-platform", "analytics_platform.an_api.application_factory:create_app", True),
    "quality": ("aios-quality-platform", "quality_platform.qa_api.application_factory:create_app", True),
    "docs": ("aios-docs-platform", "docs_platform.doc_api.application_factory:create_app", True),
    "release": ("aios-release-platform", "release_platform.release_api.application_factory:create_app", True),
    "perf": ("aios-perf-platform", "perf_platform.perf_api.application_factory:create_app", True),
}
PREFIX = "/svc/"


def _load(directory: str, target: str, factory: bool):
    path = str(ROOT / directory)
    if path not in sys.path:
        sys.path.insert(0, path)
    module_name, attr = target.split(":")
    obj = getattr(importlib.import_module(module_name), attr)
    return obj() if factory else obj


class Platform:
    """ASGI dispatcher: /svc/<name>/<rest> -> service <name> at /<rest>; /health -> combined liveness."""

    def __init__(self) -> None:
        self.apps = {name: _load(*spec) for name, spec in SERVICES.items()}

    @asynccontextmanager
    async def lifespan(self):
        async with AsyncExitStack() as stack:
            for app in self.apps.values():
                await stack.enter_async_context(app.router.lifespan_context(app))
            yield

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
            return
        path = scope.get("path", "")
        if path in ("/health", "/health/live"):
            await _json(send, 200, b'{"status":"ok","services":%d}' % len(self.apps))
            return
        if path.startswith(PREFIX):
            name, _, rest = path[len(PREFIX):].partition("/")
            app = self.apps.get(name)
            if app is not None:
                inner = dict(scope)
                inner["path"] = "/" + rest
                inner["raw_path"] = inner["path"].encode()
                inner["root_path"] = scope.get("root_path", "") + PREFIX + name
                await app(inner, receive, send)
                return
        await _json(send, 404, b'{"detail":"Not Found"}')

    async def _lifespan(self, receive, send) -> None:
        message = await receive()
        assert message["type"] == "lifespan.startup"
        try:
            async with self.lifespan():
                await send({"type": "lifespan.startup.complete"})
                await receive()  # lifespan.shutdown
        except BaseException as exc:  # noqa: BLE001 - report startup failure to the server, then re-raise
            await send({"type": "lifespan.startup.failed", "message": repr(exc)})
            raise
        await send({"type": "lifespan.shutdown.complete"})


async def _json(send, status: int, body: bytes) -> None:
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})


app = Platform()
