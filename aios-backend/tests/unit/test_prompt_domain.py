"""Unit tests for the Prompt domain aggregate — pure business logic, no DB,
no HTTP. These are the fastest tests in the suite and the ones that should
catch a broken promotion rule before anything else does.
"""

from datetime import datetime, timezone

import pytest

from app.domain.entities.prompt import MIN_PRODUCTION_EVAL_SCORE, Prompt
from app.domain.exceptions import UnprocessableStateError
from app.domain.value_objects.enums import PromptStatus


def make_prompt() -> Prompt:
    return Prompt(
        id="p1", workspace_id="ws1", name="Test Prompt", description="", target_model="claude-haiku-4.5"
    )


def test_add_version_starts_at_one():
    prompt = make_prompt()
    version = prompt.add_version("Hello {{name}}", "author1", datetime.now(timezone.utc))
    assert version.version == 1
    assert version.status == PromptStatus.DRAFT


def test_add_version_increments():
    prompt = make_prompt()
    prompt.add_version("v1 content", "author1", datetime.now(timezone.utc))
    v2 = prompt.add_version("v2 content", "author1", datetime.now(timezone.utc))
    assert v2.version == 2


def test_cannot_promote_to_production_without_eval_score():
    prompt = make_prompt()
    prompt.add_version("content", "author1", datetime.now(timezone.utc))
    with pytest.raises(UnprocessableStateError):
        prompt.promote_version(1, PromptStatus.STAGED)  # draft -> staged is fine
        prompt.promote_version(1, PromptStatus.PRODUCTION)  # staged -> production needs eval score


def test_promoting_new_production_version_demotes_previous():
    prompt = make_prompt()
    v1 = prompt.add_version("v1", "author1", datetime.now(timezone.utc))
    v1.eval_score = MIN_PRODUCTION_EVAL_SCORE
    prompt.promote_version(1, PromptStatus.STAGED)
    prompt.promote_version(1, PromptStatus.PRODUCTION)
    assert prompt.production_version.version == 1

    v2 = prompt.add_version("v2", "author1", datetime.now(timezone.utc))
    v2.eval_score = MIN_PRODUCTION_EVAL_SCORE
    prompt.promote_version(2, PromptStatus.STAGED)
    prompt.promote_version(2, PromptStatus.PRODUCTION)

    assert prompt.production_version.version == 2
    v1_after = next(v for v in prompt.versions if v.version == 1)
    assert v1_after.status == PromptStatus.ARCHIVED


def test_invalid_transition_raises():
    prompt = make_prompt()
    prompt.add_version("content", "author1", datetime.now(timezone.utc))
    with pytest.raises(UnprocessableStateError):
        prompt.promote_version(
            1, PromptStatus.PRODUCTION
        )  # draft -> production is not an allowed direct transition
