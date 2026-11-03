"""Structured-output contracts for reasoning and reflection — every
model call in this engine goes through the AI Core's StructuredOutputEngine
so "the model showed its work" is a typed object, not free text we hope
is parseable.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ReasoningStep(BaseModel):
    step: int
    thought: str
    action: str | None = Field(default=None, description="What the agent did, if anything, at this step")
    observation: str | None = Field(default=None, description="What was learned/observed as a result of the action")


class ChainOfThoughtResult(BaseModel):
    steps: list[ReasoningStep]
    final_answer: str
    confidence: float = Field(ge=0.0, le=1.0, description="The model's own estimate of how confident it is in final_answer")


class CritiqueResult(BaseModel):
    critique: str = Field(description="Specific, actionable critique of the response being reviewed")
    passed: bool = Field(description="True if the response fully and correctly satisfies the goal with no material issues")
    issues: list[str] = Field(default_factory=list, description="Discrete list of problems found, empty if passed")
    suggested_correction: str | None = Field(default=None, description="A concrete fix or improved version, if passed is False")
    confidence: float = Field(ge=0.0, le=1.0, description="The critic's confidence in its own verdict")
