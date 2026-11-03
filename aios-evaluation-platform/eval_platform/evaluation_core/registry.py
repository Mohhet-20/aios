"""EvaluationTypeRegistry: the data-driven catalog of all 16 built-in
evaluation types. Each entry describes policy/metadata only — which
metric keys are recommended by default and what a "target" for this
type typically looks like — never engine logic. Adding a 17th
evaluation type is a row insert here, not a change to the run engine,
which only ever looks up `metric_keys` off the evaluation *version*
(never branches on `category` itself)."""
from __future__ import annotations

from dataclasses import dataclass, field

from eval_platform.domain.enums import EvaluationCategory


@dataclass(frozen=True)
class EvaluationTypeSpec:
    key: str
    name: str
    description: str
    default_target_type: str
    recommended_metric_keys: list[str] = field(default_factory=list)


EVALUATION_TYPE_SPECS: list[EvaluationTypeSpec] = [
    EvaluationTypeSpec(
        EvaluationCategory.PROMPT.value, "Prompt Evaluation", "Scores a prompt's output against expected output.",
        "prompt", ["accuracy", "instruction_following", "formatting_compliance"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.AGENT.value, "Agent Evaluation", "Scores an agent's planning, tool selection, and task completion.",
        "agent", ["task_success_rate", "planning_quality", "reliability"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.WORKFLOW.value, "Workflow Evaluation", "Scores a workflow run's success, reliability, and duration.",
        "workflow", ["task_success_rate", "reliability", "latency"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.TOOL.value, "Tool Evaluation", "Scores a tool call's correctness and reliability.",
        "tool", ["accuracy", "reliability", "latency"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.MEMORY_RETRIEVAL.value, "Memory Retrieval Evaluation", "Scores retrieved memories' relevance to a query.",
        "memory_query", ["precision", "recall", "f1_score"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.KNOWLEDGE_QUALITY.value, "Knowledge Quality Evaluation", "Scores stored knowledge for accuracy and completeness.",
        "knowledge_item", ["accuracy", "response_completeness"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.LLM.value, "LLM Evaluation", "Scores a raw model response independent of any prompt template.",
        "model", ["accuracy", "consistency", "token_usage"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.REASONING.value, "Reasoning Evaluation", "Scores the quality of a chain-of-reasoning trace.",
        "reasoning_trace", ["reasoning_quality", "consistency"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.PLANNING.value, "Planning Evaluation", "Scores a generated plan's soundness and completeness.",
        "plan", ["planning_quality", "task_success_rate"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.TASK_COMPLETION.value, "Task Completion Evaluation", "Scores whether a stated task was actually completed.",
        "task", ["task_success_rate", "response_completeness"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.CONVERSATION.value, "Conversation Evaluation", "Scores a multi-turn conversation for coherence and helpfulness.",
        "conversation", ["consistency", "instruction_following", "response_completeness"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.SAFETY.value, "Safety Evaluation", "Scores a response for policy-violating or unsafe content.",
        "response", ["reliability", "consistency"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.GROUNDEDNESS.value, "Groundedness Evaluation", "Scores whether a response is supported by its source context.",
        "response_with_context", ["groundedness", "faithfulness", "hallucination_rate", "citation_quality"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.STRUCTURED_OUTPUT.value, "Structured Output Validation", "Validates a response against a declared JSON Schema.",
        "structured_response", ["json_validation", "formatting_compliance"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.API_RESPONSE.value, "API Response Validation", "Validates an API call's response shape, status, and latency.",
        "api_call", ["json_validation", "latency", "reliability"],
    ),
    EvaluationTypeSpec(
        EvaluationCategory.END_TO_END_SYSTEM.value, "End-to-End System Evaluation", "Scores a full multi-subsystem run (prompt+agent+tool+memory) as one unit.",
        "system_run", ["task_success_rate", "reliability", "cost", "latency"],
    ),
]

_BY_KEY: dict[str, EvaluationTypeSpec] = {spec.key: spec for spec in EVALUATION_TYPE_SPECS}


def get_evaluation_type_spec(category: str) -> EvaluationTypeSpec:
    from eval_platform.core.exceptions import UnknownEvaluationTypeError

    spec = _BY_KEY.get(category)
    if spec is None:
        raise UnknownEvaluationTypeError(f"unknown evaluation category '{category}'")
    return spec
