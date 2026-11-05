"""Prompt chaining: a sequence of prompt-execution steps where each step's
variables can depend on the previous step's response. This is the
building block agent/workflow logic (later) will compose — the AI Core
only needs to provide "run these steps in order, threading state through,"
not any agent-specific control flow.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ai_core.prompts.executor import PromptExecutor
from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.responses import GenerationResponse

VariableMapper = Callable[[dict, "GenerationResponse | None"], dict]


@dataclass
class PromptStep:
    templates: list[PromptTemplate]
    variable_mapper: VariableMapper
    model: str | None = None
    provider: str | None = None
    temperature: float = 0.7


class PromptChain:
    def __init__(self, steps: list[PromptStep], executor: PromptExecutor):
        self.steps = steps
        self.executor = executor

    async def run(self, initial_variables: dict | None = None) -> list[GenerationResponse]:
        chain_state = dict(initial_variables or {})
        previous_response: GenerationResponse | None = None
        responses: list[GenerationResponse] = []
        for step in self.steps:
            step_variables = step.variable_mapper(chain_state, previous_response)
            response = await self.executor.execute(
                step.templates, step_variables, model=step.model, provider=step.provider, temperature=step.temperature
            )
            responses.append(response)
            previous_response = response
            chain_state["previous_output"] = response.content
        return responses
