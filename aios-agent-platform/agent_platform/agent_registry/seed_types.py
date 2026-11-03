"""Seed data for the 17 built-in specialized agent types the spec calls
for. This is deliberately DATA, not Python classes — the whole point of
`AgentTypeModel` being a table is that a new specialist (built-in or
customer-defined) is a row insert, never a code change. Re-running
`seed_builtin_agent_types` is idempotent (skips any key that already
exists), so it's safe to call on every app startup.
"""
from __future__ import annotations

from agent_platform.domain.enums import AgentCategory
from agent_platform.models.agent_type import AgentTypeModel
from agent_platform.repositories.registry import RepositoryRegistry

BUILTIN_AGENT_TYPES: list[dict] = [
    dict(key="planner", name="Planner Agent", category=AgentCategory.PLANNER, description="Decomposes goals into ordered, dependency-aware subtasks.",
         default_instructions="You are a planning specialist. Break the given goal into the smallest set of concrete, verifiable subtasks, identify dependencies between them, and assign a priority to each. Never execute subtasks yourself.",
         default_capabilities=["goal_decomposition", "dependency_analysis", "priority_assignment"], default_skills=["structured_planning"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 4000, "timeout_seconds": 60}),
    dict(key="research", name="Research Agent", category=AgentCategory.RESEARCH, description="Gathers information from external and internal sources.",
         default_instructions="You are a research specialist. Gather accurate, sourced information relevant to the task using the tools available to you. Cite what you find; never fabricate sources.",
         default_capabilities=["information_gathering", "source_evaluation"], default_skills=["web_search", "synthesis"],
         default_tool_names=["web_search", "document_parser"], default_resource_limits={"max_tokens_per_run": 6000, "timeout_seconds": 90}),
    dict(key="reasoning", name="Reasoning Agent", category=AgentCategory.REASONING, description="Performs multi-step logical reasoning over a problem.",
         default_instructions="You are a reasoning specialist. Work through the problem step by step, making each inference explicit before drawing a conclusion.",
         default_capabilities=["chain_of_thought", "tree_of_thought"], default_skills=["logical_inference"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 8000, "timeout_seconds": 120}),
    dict(key="critic", name="Critic Agent", category=AgentCategory.CRITIC, description="Critiques another agent's output for flaws before it ships.",
         default_instructions="You are a critic. Identify concrete flaws, gaps, and risks in the given output. Be specific and actionable; do not rewrite the output yourself.",
         default_capabilities=["critique", "risk_identification"], default_skills=["adversarial_review"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 3000, "timeout_seconds": 60}),
    dict(key="reviewer", name="Reviewer Agent", category=AgentCategory.REVIEWER, description="Reviews work for quality/style/completeness against a rubric.",
         default_instructions="You are a reviewer. Check the given output against the stated requirements and quality bar. Report pass/fail per criterion with a brief justification.",
         default_capabilities=["rubric_evaluation"], default_skills=["quality_review"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 3000, "timeout_seconds": 60}),
    dict(key="verifier", name="Verifier Agent", category=AgentCategory.VERIFIER, description="Verifies factual/logical correctness before final output.",
         default_instructions="You are a verifier. Check every factual and logical claim in the given output for correctness. Flag anything unverifiable or wrong.",
         default_capabilities=["fact_checking", "logical_verification"], default_skills=["verification"],
         default_tool_names=["web_search"], default_resource_limits={"max_tokens_per_run": 4000, "timeout_seconds": 90}),
    dict(key="coding", name="Coding Agent", category=AgentCategory.CODING, description="Writes, edits, and explains code.",
         default_instructions="You are a coding specialist. Write correct, minimal, well-structured code for the given task. Explain non-obvious decisions briefly.",
         default_capabilities=["code_generation", "code_review"], default_skills=["software_engineering"],
         default_tool_names=["python_execution", "file_analysis"], default_resource_limits={"max_tokens_per_run": 8000, "timeout_seconds": 180}),
    dict(key="documentation", name="Documentation Agent", category=AgentCategory.DOCUMENTATION, description="Produces clear documentation from source material.",
         default_instructions="You are a documentation specialist. Turn the given material into clear, well-organized documentation for its intended audience.",
         default_capabilities=["technical_writing"], default_skills=["documentation"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 6000, "timeout_seconds": 90}),
    dict(key="summarization", name="Summarization Agent", category=AgentCategory.SUMMARIZATION, description="Condenses long content into accurate summaries.",
         default_instructions="You are a summarization specialist. Produce a faithful, concise summary of the given content, preserving every material fact.",
         default_capabilities=["summarization"], default_skills=["condensation"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 3000, "timeout_seconds": 60}),
    dict(key="retrieval", name="Retrieval Agent", category=AgentCategory.RETRIEVAL, description="Retrieves relevant context from knowledge stores.",
         default_instructions="You are a retrieval specialist. Given a query, retrieve the most relevant stored context and return it with relevance rationale.",
         default_capabilities=["semantic_retrieval"], default_skills=["retrieval"],
         default_tool_names=["database_query"], default_resource_limits={"max_tokens_per_run": 2000, "timeout_seconds": 30}),
    dict(key="memory", name="Memory Agent", category=AgentCategory.MEMORY, description="Manages reads/writes to the (future) Memory Platform on behalf of other agents.",
         default_instructions="You are a memory specialist. Store and retrieve information from memory precisely, without altering its meaning.",
         default_capabilities=["memory_read", "memory_write"], default_skills=["memory_management"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 1500, "timeout_seconds": 20}),
    dict(key="tool", name="Tool Agent", category=AgentCategory.TOOL, description="Specializes in invoking a specific tool or API correctly.",
         default_instructions="You are a tool-invocation specialist. Translate the request into correct tool calls, validate the results, and report back precisely.",
         default_capabilities=["tool_invocation"], default_skills=["api_usage"],
         default_tool_names=["api_call"], default_resource_limits={"max_tokens_per_run": 2000, "timeout_seconds": 45}),
    dict(key="workflow", name="Workflow Agent", category=AgentCategory.WORKFLOW, description="Drives a multi-step workflow's agent-facing steps forward.",
         default_instructions="You are a workflow specialist. Advance the current workflow step, respecting any pause/approval gates encountered.",
         default_capabilities=["workflow_execution"], default_skills=["process_management"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 2000, "timeout_seconds": 60}),
    dict(key="reporting", name="Reporting Agent", category=AgentCategory.REPORTING, description="Compiles execution results into a stakeholder-facing report.",
         default_instructions="You are a reporting specialist. Compile the given results into a clear report for the intended audience, leading with the outcome.",
         default_capabilities=["report_generation"], default_skills=["reporting"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 4000, "timeout_seconds": 60}),
    dict(key="coordinator", name="Coordinator Agent", category=AgentCategory.COORDINATOR, description="Supervises and routes work across a team of agents.",
         default_instructions="You are a coordinator. Decide which specialist should handle the next step, monitor progress, and resolve conflicts between agents.",
         default_capabilities=["delegation", "supervision"], default_skills=["orchestration"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 3000, "timeout_seconds": 45}),
    dict(key="human_approval", name="Human Approval Agent", category=AgentCategory.HUMAN_APPROVAL, description="Represents a human-in-the-loop approval checkpoint.",
         default_instructions="You represent a human approval gate. Summarize what is being requested and why, clearly enough for a human to decide quickly.",
         default_capabilities=["approval_summarization"], default_skills=["human_interface"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 1000, "timeout_seconds": 30}),
    dict(key="system", name="System Agent", category=AgentCategory.SYSTEM, description="Performs internal platform maintenance tasks (health checks, cleanup).",
         default_instructions="You are a system agent performing internal platform operations. Act deterministically and report status precisely.",
         default_capabilities=["system_maintenance"], default_skills=["operations"],
         default_tool_names=[], default_resource_limits={"max_tokens_per_run": 500, "timeout_seconds": 15}),
]


async def seed_builtin_agent_types(repos: RepositoryRegistry) -> list[AgentTypeModel]:
    created = []
    for spec in BUILTIN_AGENT_TYPES:
        existing = await repos.agent_types.get_by_key(spec["key"])
        if existing is not None:
            created.append(existing)
            continue
        model = AgentTypeModel(
            key=spec["key"], name=spec["name"], category=spec["category"].value, description=spec["description"],
            default_instructions=spec["default_instructions"], default_capabilities=spec["default_capabilities"],
            default_skills=spec["default_skills"], default_tool_names=spec["default_tool_names"],
            default_resource_limits=spec["default_resource_limits"], is_builtin=True,
        )
        created.append(await repos.agent_types.add(model))
    return created
