# AIOS — Enterprise AI Core & LLM Gateway

the unified abstraction layer over every AI capability for the Enterprise AI Operating System. This is where every model provider, every inference call, every prompt, every tool call, and every dollar of AI spend flows through — the AIOS backend (the core backend) and everything after it (agents, memory, workflows, evaluation) are meant to sit on top of this, never talk to a provider SDK directly.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # add real provider API keys for live use

uvicorn ai_core.main:app --reload --port 8100
# http://localhost:8100/docs — OpenAPI/Swagger
# http://localhost:8100/health/live, /health/ready, /metrics

pytest                         # 126 tests, all green, zero network calls
```

Every provider adapter talks real HTTP (`httpx.AsyncClient`) in the shape each provider actually expects — the test suite never hits a real network; it verifies wire-format correctness via `httpx.MockTransport` and engine orchestration via scripted provider doubles. Point `.env`'s provider keys at real accounts to use it live; nothing in the code path changes between test and production, only what's on the other end of the HTTP call.

## Architecture

**Providers** (`ai_core/providers/`): one `ModelProviderAdapter` per backend — OpenAI, Azure OpenAI, Anthropic, Gemini, HuggingFace Inference, Ollama, vLLM, LM Studio, local Transformers (9 total, all wired in `registry_bootstrap.py`). Anthropic, Gemini, and HuggingFace each speak a genuinely different wire format (system-prompt-as-field, function-call-as-content-block, single-prompt-string) and each adapter bridges its own format to the canonical `ChatMessage`/`GenerationResponse` schema — nothing above this layer ever sees a provider-specific shape. Adding a 10th provider is one new file plus one line in `registry_bootstrap.py`.

**Model Registry** (`ai_core/registry/`): `ModelMetadata` tracks provider, context window, capabilities (streaming/vision/audio/tool-calling/JSON-output/embedding/reasoning), pricing, status, and a rolling latency average, per model. Seeded with 19 real models across all 9 providers; dynamic registration means adding a new model — or the prompt platform's future reasoning models — is a `registry.register()` call, not a schema change.

**Model Router** (`ai_core/router/`): turns a request into an ordered fallback chain. Eleven routing strategies (task-based, capability, cost-aware, latency-aware, priority, regional, load-balancing, canary, A/B, rule-based, and a documented ML-based seam) compose as pipeline stages via `RoutingPolicy` — `RoutingPolicy.default()`, `.cost_optimized()`, and `.latency_optimized()` ship out of the box. The router also auto-detects capability requirements from the request itself (streaming, tool calling, JSON output, and — a gap caught during testing — vision/audio from multimodal message content), so a caller never has to manually flag "this needs a vision model."

**Execution Engine** (`ai_core/execution/`): the only place inference actually happens. Standard, streaming, batch, and concurrent inference; per-attempt timeouts; exponential-backoff retries for transient failures; automatic provider failover across the router's fallback chain; request/response validation; cost and token accounting; full execution metadata (which model actually served it, retry count, whether fallback fired) on every response. Streaming fails over before the first token only — once content is visible to a user, a later error is raised rather than silently splicing in a different model's output.

**Prompt Execution** (`ai_core/prompts/`): a dependency-free `{{variable}}` template engine (deliberately not Jinja2 — no expression-evaluation attack surface), message composition (system/developer/few-shot/user), a lightweight versioned template registry, and `PromptChain` for sequential multi-step execution where each step's variables can depend on the previous step's response.

**Structured Output** (`ai_core/structured_output/`): JSON-schema-constrained generation, tolerant parsing (handles markdown-fenced JSON and prose-wrapped JSON), Pydantic validation, and automatic **response repair** — an invalid response gets re-prompted with the validation error and retried up to a configurable limit before giving up, with a heuristic confidence score that decays per repair attempt.

**Tool/Function Calling** (`ai_core/tool_calling/`): a tool registry, JSON-Schema argument validation, permission checks, a sandboxing seam (in-process today, documented swap point for real isolation), parallel and sequential execution, and an MCP compatibility bridge (`from_mcp_tool_spec`/`to_mcp_tool_spec`) so a future real MCP client integration is a translation layer, not a redesign.

**Multimodal & Embeddings** (`ai_core/vision/`, `ai_core/audio/`, `ai_core/embeddings/`): builders for image/audio message construction; a unified `EmbeddingEngine` with per-item caching (partial cache hits only call the provider for misses), batch support, and version tagging; an `InMemoryVectorStore` + `SimilaritySearchService` as the integration point for a future pgvector/Qdrant/Pinecone swap.

**Cost & Observability** (`ai_core/cost/`, `ai_core/observability/`): `CostCalculator` computes real per-request cost from registry pricing (including a cached-token discount rate); `UsageTracker` aggregates tokens/cost by organization/user/project across daily and monthly windows and enforces cost and rate limits before a request is even routed. `StructlogObservabilityLogger` and `PrometheusObservabilityLogger` both implement the same logging interface and run together via `CompositeObservabilityLogger` — every request/failure/retry/fallback/tool-call is logged and counted, with correlation IDs, and deliberately without raw prompt/completion content (PII/secret exposure risk).

**Gateway** (`ai_core/gateway/`): a FastAPI HTTP front door (`/v1/generate`, `/v1/generate/stream` via SSE, `/v1/embeddings`, `/v1/models`, `/v1/tools`, `/v1/usage`, plus `/health/live`, `/health/ready`, `/metrics`) for callers that want a network boundary instead of an in-process import — every route delegates to the exact same engines a Python caller would use directly, via `ai_core/bootstrap.py`'s one-call wiring of the whole stack.

## Testing

126 tests, all passing in a single combined run with zero real network calls: provider wire-format tests (per adapter, via `httpx.MockTransport`), routing tests (all 11 strategies plus fallback-chain construction), execution engine tests (retries, failover, engine-level timeouts, cancellation, streaming failover, batch/concurrent execution), prompt engine tests, structured-output repair tests, tool-calling tests (parallel/sequential/permission-denied/timeout/sandboxed), multimodal/embedding tests (cache hit/miss/partial-hit, vector store ranking), cost/usage tests (limit enforcement, multi-scope aggregation), observability tests, gateway API tests, dedicated performance and failure-recovery suites, and a feature-flag enforcement suite.

Three real bugs were found and fixed by writing these tests, not just import checks: (1) embedding-only models were leaking into the general chat-routing pool because nothing excluded them — `route()` now explicitly excludes `Capability.EMBEDDING`-only models from generation candidates; (2) the `cost_optimized`/`latency_optimized` routing policies had `PriorityStrategy` running last, silently undoing the cost/latency ordering they exist to enforce — fixed by making the named strategy the final word on ordering for those policies; (3) the router never inferred `Capability.VISION`/`AUDIO_INPUT` requirements from multimodal message content, meaning a caller sending an image could silently get routed to a text-only model — fixed by inspecting message content parts during capability detection.

## Self-review (Principal AI Platform Engineer)

**Can new providers be added without rewriting the architecture?** Yes — this was tested, not just designed for. Nine providers ship today across three genuinely different wire formats (OpenAI-style chat completions, Anthropic's content-block messages API, Gemini's `generateContent`), and HuggingFace's classic single-prompt-string API proves the abstraction absorbs an even more different shape without leaking into the execution engine. A tenth provider is a new `ModelProviderAdapter` subclass and one registration line.

**Can future reasoning models integrate easily?** The registry already models `Capability.REASONING` and seeds `o1` as a reasoning-tagged model with no tool-calling/streaming (matching its real constraints); routing by task tag (`routing_hints.task="reasoning"`) already works end to end. A new reasoning model — including one with a genuinely new capability, like native chain-of-thought exposure — is a registry entry plus, if the wire format is new, one adapter.

**Can enterprise customers use multiple providers simultaneously?** Yes, natively — the router's fallback chain and load-balancing/canary/A-B strategies exist specifically so a single request stream can span providers, and `UsageTracker`'s org/user/project scoping means multi-tenant cost attribution works without each tenant needing separate infrastructure.

**Can costs be accurately monitored?** Real per-request cost (not estimated) is computed from actual token usage against registry pricing, including a cached-token discount rate, on every response — and `UsageTracker` enforces daily/monthly cost ceilings *before* a request is routed, not after the bill arrives. The honest gap: registry pricing is illustrative seed data that needs an operational refresh process (dynamic `registry.register()` makes that mechanically easy; keeping it *current* is a process question, not a code one).

**Can failures recover automatically?** Retries with exponential backoff for transient errors, automatic failover across the router's ordered candidate chain for both generation and embeddings, and a flaky-then-recovers scenario is covered by a dedicated failure-recovery test. The one deliberate non-recovery: mid-stream failures after the first token are raised, not silently failed over, because splicing two models' output into one response would be a worse failure mode than a clean error.

**Can this become the foundation for agents, memory, workflows, and evaluation?** That's what every design choice here was made for. `PromptChain` is the primitive multi-step agent reasoning composes from. `SimilaritySearchService` + `InMemoryVectorStore` (swappable) is what a memory subsystem builds on. `ToolExecutor`'s permission/sandboxing seams are exactly what agent tool use needs. `UsageTracker` and the observability layer are what an evaluation harness would query for cost/latency/failure-rate comparisons across model variants. Nothing here was built as a one-off's scope — it was built as the layer everything else in AIOS sits on.

## Known limitations (by design)

No agents, memory, workflows, or evaluation logic — those are explicitly out of scope and build on top of what's here. Tool sandboxing runs in-process (`NullToolSandbox`); real isolation is a documented swap point. The vector store is in-memory/O(n); a real deployment needs pgvector/Qdrant/Pinecone behind the same three-method interface. Registry pricing is illustrative seed data, not a live feed from provider pricing pages. The event bus task queue seen in the core backend are not duplicated here — this AI Core is a synchronous-await library plus an optional HTTP gateway; background job orchestration remains the backend's responsibility, calling into this layer.
