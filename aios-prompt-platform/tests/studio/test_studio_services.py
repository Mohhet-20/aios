import pytest

from ai_core.schemas.responses import StreamChunk

from prompt_platform.core.exceptions import ConflictError, ValidationError
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_editor.autosave import AutosaveService
from prompt_platform.prompt_editor.execution import StudioExecutionService
from prompt_platform.prompt_editor.formatting import format_template
from prompt_platform.prompt_editor.preview import PreviewService
from prompt_platform.prompt_editor.validation import validate_draft, validate_draft_or_raise


def test_validate_draft_flags_undeclared_and_unused_variables():
    report = validate_draft(
        system_template=None, developer_template=None, user_template="Hi {{name}}, {{unused_declared}}",
        variables_schema=[{"name": "unused_declared"}], parameters={}, max_chars=1000,
    )
    assert not report.is_valid
    assert any("name" in i.message for i in report.errors)
    assert report.warnings == []  # unused_declared IS used, so no warning — regression guard on the test's own intent
    # Now check the genuinely-unused case:
    report2 = validate_draft(
        system_template=None, developer_template=None, user_template="Hi {{name}}",
        variables_schema=[{"name": "name"}, {"name": "never_used"}], parameters={}, max_chars=1000,
    )
    assert report2.is_valid
    assert any("never_used" in i.message for i in report2.warnings)


def test_validate_draft_empty_user_template_is_error():
    report = validate_draft(system_template=None, developer_template=None, user_template="   ", variables_schema=[], parameters={}, max_chars=1000)
    assert not report.is_valid


def test_validate_draft_rejects_bad_temperature():
    report = validate_draft(
        system_template=None, developer_template=None, user_template="hi", variables_schema=[],
        parameters={"temperature": 5.0}, max_chars=1000,
    )
    assert not report.is_valid


def test_validate_draft_or_raise_raises_validation_error():
    with pytest.raises(ValidationError):
        validate_draft_or_raise(system_template=None, developer_template=None, user_template="", variables_schema=[], parameters={}, max_chars=1000)


def test_format_template_trims_and_collapses():
    result = format_template("Hello   \n\n\n\nWorld  \n\n")
    assert result == "Hello\n\nWorld"


def test_format_template_none_passthrough():
    assert format_template(None) is None


def test_preview_service_renders_and_estimates_tokens(scripted_ai_core):
    context, _ = scripted_ai_core
    svc = PreviewService(context)
    result = svc.render(
        system_template="You are {{persona}}.", developer_template=None, user_template="Q: {{q}}",
        variables={"persona": "terse", "q": "2+2?"}, parameters={"model": "m1", "provider": "test"},
    )
    assert result.rendered_messages[0]["content"] == "You are terse."
    assert result.token_estimate > 0
    assert result.context_window.model == "m1"
    assert result.context_window.percent_used is not None


def test_preview_service_raises_validation_error_on_missing_variable(scripted_ai_core):
    context, _ = scripted_ai_core
    svc = PreviewService(context)
    with pytest.raises(ValidationError):
        svc.render(system_template=None, developer_template=None, user_template="Hi {{name}}", variables={}, parameters={})


@pytest.mark.asyncio
async def test_studio_execution_run_returns_response(scripted_ai_core):
    context, provider = scripted_ai_core
    provider.push(__import__("tests.conftest", fromlist=["make_response"]).make_response("Hello back!"))
    svc = StudioExecutionService(context)
    response = await svc.run(
        system_template=None, developer_template=None, user_template="Hi {{name}}",
        variables={"name": "Ada"}, parameters={"model": "m1", "provider": "test"},
    )
    assert response.content == "Hello back!"


@pytest.mark.asyncio
async def test_studio_execution_run_stream_yields_chunks(scripted_ai_core):
    context, provider = scripted_ai_core
    provider.push([StreamChunk(request_id="r1", delta="Hi", is_final=False), StreamChunk(request_id="r1", delta="!", is_final=True)])
    svc = StudioExecutionService(context)
    chunks = [
        c async for c in svc.run_stream(
            system_template=None, developer_template=None, user_template="hi",
            variables={}, parameters={"model": "m1", "provider": "test"},
        )
    ]
    assert "".join(c.delta for c in chunks) == "Hi!"


@pytest.mark.asyncio
async def test_studio_execution_run_structured_parses_valid_json(scripted_ai_core):
    context, provider = scripted_ai_core
    provider.push(__import__("tests.conftest", fromlist=["make_response"]).make_response('{"answer": 4}'))
    svc = StudioExecutionService(context)
    result = await svc.run_structured(
        system_template=None, developer_template=None, user_template="2+2?", variables={},
        parameters={"model": "m1", "provider": "test"}, json_schema={"type": "object", "properties": {"answer": {"type": "integer"}}},
    )
    assert result["valid_json"] is True
    assert result["parsed"] == {"answer": 4}


@pytest.mark.asyncio
async def test_studio_execution_run_structured_reports_invalid_json(scripted_ai_core):
    context, provider = scripted_ai_core
    provider.push(__import__("tests.conftest", fromlist=["make_response"]).make_response("not json"))
    svc = StudioExecutionService(context)
    result = await svc.run_structured(
        system_template=None, developer_template=None, user_template="hi", variables={},
        parameters={"model": "m1", "provider": "test"}, json_schema={"type": "object"},
    )
    assert result["valid_json"] is False


@pytest.mark.asyncio
async def test_autosave_persists_draft_with_optimistic_locking(repos):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="P", slug="p", owner_id="u1"))
    version = await repos.versions.add(PromptVersionModel(prompt_id=prompt.id, version_number=1, user_template="old text", version=1))

    svc = AutosaveService(repos)
    updated = await svc.save_draft(version.id, expected_version=1, user_template="  new text  \n\n\n")
    # format_template trims trailing whitespace per line and collapses
    # blank lines, but deliberately preserves leading whitespace/indentation.
    assert updated.user_template == "  new text"
    assert updated.version == 2


@pytest.mark.asyncio
async def test_autosave_conflict_on_stale_version(repos):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS2", slug="ws2", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj2", slug="proj2"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="P2", slug="p2", owner_id="u1"))
    version = await repos.versions.add(PromptVersionModel(prompt_id=prompt.id, version_number=1, user_template="text", version=1))

    svc = AutosaveService(repos)
    with pytest.raises(ConflictError):
        await svc.save_draft(version.id, expected_version=99, user_template="x")
