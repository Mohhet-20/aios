import pytest

from prompt_platform.core.exceptions import DependencyCycleError, EvalGateNotMetError, InvalidTransitionError
from prompt_platform.domain.dependency_graph import validate_no_cycle
from prompt_platform.domain.entities import Prompt, PromptVersion
from prompt_platform.domain.enums import VersionBranch, VersionStatus


def _prompt() -> Prompt:
    return Prompt(id="p1", project_id="proj1", workspace_id="ws1", name="Greeting", slug="greeting", owner_id="u1")


def test_add_version_increments_number_and_links_parent():
    prompt = _prompt()
    v1 = prompt.add_version(version_id="v1", user_template="Hi {{name}}")
    v2 = prompt.add_version(version_id="v2", user_template="Hello {{name}}")
    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v2.parent_version_id == "v1"


def test_version_approval_workflow_happy_path():
    v = PromptVersion(id="v1", prompt_id="p1", version_number=1, user_template="hi")
    v.submit_for_review("reviewer-request-actor")
    assert v.status == VersionStatus.IN_REVIEW
    v.approve("reviewer1")
    assert v.status == VersionStatus.APPROVED
    assert v.approved_by == "reviewer1"


def test_version_rejection_and_resubmit():
    v = PromptVersion(id="v1", prompt_id="p1", version_number=1, user_template="hi")
    v.submit_for_review("actor")
    v.reject("reviewer1", "not clear enough")
    assert v.status == VersionStatus.REJECTED
    assert v.rejection_reason == "not clear enough"
    v.resubmit()
    assert v.status == VersionStatus.DRAFT


def test_invalid_transition_raises():
    v = PromptVersion(id="v1", prompt_id="p1", version_number=1, user_template="hi")
    with pytest.raises(InvalidTransitionError):
        v.approve("actor")  # can't approve straight from DRAFT


def test_promote_requires_approved_status():
    v = PromptVersion(id="v1", prompt_id="p1", version_number=1, user_template="hi")
    with pytest.raises(InvalidTransitionError):
        v.promote(VersionBranch.STABLE, min_production_eval_score=85.0)


def test_promote_to_production_requires_eval_gate():
    v = PromptVersion(id="v1", prompt_id="p1", version_number=1, user_template="hi")
    v.submit_for_review("actor")
    v.approve("reviewer1")
    with pytest.raises(EvalGateNotMetError):
        v.promote(VersionBranch.PRODUCTION, min_production_eval_score=85.0)
    v.record_eval_score(90.0)
    v.promote(VersionBranch.PRODUCTION, min_production_eval_score=85.0)
    assert v.branch == VersionBranch.PRODUCTION


def test_promote_to_stable_does_not_require_eval_score():
    v = PromptVersion(id="v1", prompt_id="p1", version_number=1, user_template="hi")
    v.submit_for_review("actor")
    v.approve("reviewer1")
    v.promote(VersionBranch.STABLE, min_production_eval_score=85.0)
    assert v.branch == VersionBranch.STABLE


def test_promoting_new_production_version_demotes_previous_to_stable():
    prompt = _prompt()
    v1 = prompt.add_version(version_id="v1", user_template="v1 text")
    v2 = prompt.add_version(version_id="v2", user_template="v2 text")
    for v in (v1, v2):
        v.submit_for_review("actor")
        v.approve("reviewer1")
        v.record_eval_score(95.0)

    prompt.promote_version(v1, VersionBranch.PRODUCTION, min_production_eval_score=85.0)
    assert prompt.production_version_id == "v1"

    prompt.promote_version(v2, VersionBranch.PRODUCTION, min_production_eval_score=85.0)
    assert prompt.production_version_id == "v2"
    assert v1.branch == VersionBranch.STABLE
    assert prompt.stable_version_id == "v1"


def test_dependency_cycle_detection_direct():
    with pytest.raises(DependencyCycleError):
        validate_no_cycle(existing_edges=[], new_edge=("a", "a"))


def test_dependency_cycle_detection_transitive():
    existing = [("b", "c"), ("c", "a")]
    with pytest.raises(DependencyCycleError):
        validate_no_cycle(existing_edges=existing, new_edge=("a", "b"))  # a->b->c->a


def test_dependency_no_cycle_is_allowed():
    existing = [("b", "c")]
    validate_no_cycle(existing_edges=existing, new_edge=("a", "b"))  # a->b->c, no cycle
