"""Seed a coherent demo organisation into running AIOS services, through their public REST APIs only.

    python scripts/seed_demo.py                    # services on the default local ports (scripts/dev.py)
    AIOS_INTERNAL_TOKEN=... python scripts/seed_demo.py
    AIOS_SERVICES_BASE_URL=http://127.0.0.1:8000/svc python scripts/seed_demo.py   # all services in one process

Creates one verified demo user and organisation in the identity service, a "Customer Operations" workspace in each
domain service, and realistic agents, prompts, workflows, tools, evaluations and datasets inside it. Idempotent:
running it again reuses what exists. Everything it creates is labelled as demo data. The demo account is printed at
the end; set AIOS_DEMO_EMAIL / AIOS_DEMO_PASSWORD to choose it.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

PORTS = {"identity": 8008, "prompt": 8002, "agent": 8003, "workflow": 8005, "tool": 8006, "evaluation": 8007}
HOST = os.environ.get("AIOS_SERVICE_HOST", "127.0.0.1")
BASE = os.environ.get("AIOS_SERVICES_BASE_URL", "").rstrip("/")  # <base>/<service>, as in the console's edge
TOKEN = os.environ.get("AIOS_INTERNAL_TOKEN", "")
EMAIL = os.environ.get("AIOS_DEMO_EMAIL", "demo@aios.dev")
PASSWORD = os.environ.get("AIOS_DEMO_PASSWORD", "Northwind-Demo-2026!")
ORG_NAME = "Northwind Operations (demo)"
WORKSPACE = {"name": "Customer Operations", "slug": "customer-ops"}


class ApiError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status


def call(service: str, method: str, path: str, body: dict | None = None, *, user: str | None = None):
    url = f"{BASE}/{service}{path}" if BASE else f"http://{HOST}:{PORTS[service]}{path}"
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["X-Internal-Token"] = TOKEN
    if user:
        headers["X-User-Id"] = user
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)  # noqa: S310 - local services
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, exc.read().decode(errors="replace")) from None


def items(payload) -> list[dict]:
    if isinstance(payload, list):
        return payload
    for key in ("items", "results", "data"):
        if isinstance(payload, dict) and isinstance(payload.get(key), list):
            return payload[key]
    return []


def demo_user() -> tuple[str, str]:
    """Returns (user_id, organization_id), creating and verifying the account the first time."""
    try:
        reg = call("identity", "POST", "/api/v1/auth/register",
                   {"email": EMAIL, "password": PASSWORD, "display_name": "Demo Visitor"})
        call("identity", "POST", "/api/v1/auth/verify-email", {"token": reg["verification_token"]})
    except ApiError as exc:
        if exc.status not in (400, 409, 422):
            raise
    user = call("identity", "POST", "/api/v1/auth/login", {"email": EMAIL, "password": PASSWORD})
    org_id = user.get("primary_organization_id")
    if not org_id:
        org = call("identity", "POST", "/api/v1/organizations",
                   {"name": ORG_NAME, "owner_user_id": user["id"], "slug": "northwind-demo"})
        org_id = org["id"]
    return user["id"], org_id


def workspace(service: str, org_id: str) -> str:
    existing = items(call(service, "GET", f"/api/v1/workspaces?organization_id={org_id}"))
    if existing:
        return existing[0]["id"]
    return call(service, "POST", "/api/v1/workspaces", {**WORKSPACE, "organization_id": org_id})["id"]


def ensure(service: str, list_path: str, create_path: str, wanted: list[dict], *, key: str = "name", user=None):
    have = {i.get(key) for i in items(call(service, "GET", list_path, user=user))}
    made = 0
    for body in wanted:
        if body[key] not in have:
            call(service, "POST", create_path, body, user=user)
            made += 1
    return made


def main() -> int:
    user_id, org_id = demo_user()
    print(f"identity    user {EMAIL} in organisation {org_id}")

    ws = workspace("agent", org_id)
    call("agent", "POST", "/api/v1/agent-types/seed-builtin")
    types = {t["key"]: t["id"] for t in items(call("agent", "GET", "/api/v1/agent-types"))}
    agents = [
        ("Support Triage Coordinator", "coordinator", "Classifies inbound tickets and routes them to the right queue.", ["triage", "routing"]),
        ("Refund Policy Researcher", "research", "Looks up refund policy clauses and cites them.", ["retrieval", "policy"]),
        ("Escalation Planner", "planner", "Breaks complex escalations into reviewed steps.", ["planning"]),
        ("Thread Summariser", "summarization", "Summarises long threads for a tier-2 handover.", ["summaries"]),
        ("Reply QA Reviewer", "reviewer", "Scores drafted replies against the style guide.", ["review", "quality"]),
    ]
    wanted = [{"workspace_id": ws, "agent_type_id": types[t], "name": n, "owner_id": user_id,
               "description": d, "capabilities": c, "tags": ["demo"]} for n, t, d, c in agents]
    made = ensure("agent", f"/api/v1/agents?workspace_id={ws}&page_size=100", "/api/v1/agents", wanted)
    for a in items(call("agent", "GET", f"/api/v1/agents?workspace_id={ws}&page_size=100")):
        if a.get("status") in ("draft", "inactive", "created") and a["name"] != "Reply QA Reviewer":
            try:
                call("agent", "POST", f"/api/v1/agents/{a['id']}/activate")
            except ApiError:
                pass
    print(f"agents      {made} created in workspace {ws}")

    ws = workspace("prompt", org_id)
    projects = items(call("prompt", "GET", f"/api/v1/workspaces/{ws}/projects"))
    project = projects[0]["id"] if projects else call(
        "prompt", "POST", f"/api/v1/workspaces/{ws}/projects", {"name": "Support Assistant", "slug": "support-assistant"})["id"]
    prompts = [("Ticket classifier", "Labels a ticket with intent, urgency and product area."),
               ("Refund reply", "Drafts a refund decision reply that cites the policy clause."),
               ("Escalation summary", "Summarises a thread for a tier-2 handover."),
               ("Tone rewrite", "Rewrites a reply in the brand voice without changing facts.")]
    made = ensure("prompt", f"/api/v1/prompts?workspace_id={ws}", "/api/v1/prompts",
                  [{"workspace_id": ws, "project_id": project, "name": n, "description": d} for n, d in prompts], user=user_id)
    print(f"prompts     {made} created")

    ws = workspace("workflow", org_id)
    flows = [("Inbound ticket triage", "ai_agent", "Classify, enrich and route every new ticket."),
             ("Refund approval", "approval", "Agent drafts a decision; a human approves refunds over $200."),
             ("Nightly knowledge sync", "knowledge_pipeline", "Re-index the help centre into memory."),
             ("CSAT follow-up", "notification", "Email a survey 24 hours after a ticket closes.")]
    made = ensure("workflow", f"/api/v1/workflows?workspace_id={ws}&page_size=100", "/api/v1/workflows",
                  [{"workspace_id": ws, "name": n, "owner_id": user_id, "category": c, "description": d, "tags": ["demo"]}
                   for n, c, d in flows])
    print(f"workflows   {made} created")

    ws = workspace("tool", org_id)
    tools = [("Help-centre search", "web_search", "Searches the public help centre."),
             ("Order lookup API", "rest_api", "Reads order status from the commerce API."),
             ("Refund ledger CSV", "csv_processor", "Parses the weekly refund ledger export."),
             ("Policy PDF reader", "pdf_reader", "Extracts clauses from policy documents.")]
    made = ensure("tool", f"/api/v1/tools?workspace_id={ws}&page_size=100", "/api/v1/tools",
                  [{"workspace_id": ws, "organization_id": org_id, "name": n, "owner_id": user_id, "category": c,
                    "description": d, "tags": ["demo"]} for n, c, d in tools])
    print(f"tools       {made} created")

    ws = workspace("evaluation", org_id)
    evals = [("Reply groundedness", "groundedness", "Are replies supported by the cited policy?"),
             ("Triage accuracy", "task_completion", "Does the classifier pick the right queue?"),
             ("Safety screen", "safety", "Refuses to disclose personal data or promise refunds it can't.")]
    made = ensure("evaluation", f"/api/v1/evaluations?workspace_id={ws}&page_size=100", "/api/v1/evaluations",
                  [{"workspace_id": ws, "organization_id": org_id, "name": n, "owner_id": user_id, "category": c,
                    "description": d, "tags": ["demo"]} for n, c, d in evals])
    made += ensure("evaluation", f"/api/v1/datasets?workspace_id={ws}&page_size=100", "/api/v1/datasets",
                   [{"workspace_id": ws, "organization_id": org_id, "name": "Golden support tickets", "owner_id": user_id,
                     "dataset_type": "golden", "description": "120 hand-labelled tickets (synthetic)."}])
    print(f"evaluation  {made} created")

    print(f"\nDemo account: {EMAIL} / {PASSWORD}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ApiError, OSError) as exc:
        print(f"seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
