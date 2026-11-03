import json

import httpx
from click.testing import CliRunner

import aios_cli.main as main_module
from aios_cli.config import CliConfig, load_config, save_config


def _patch_client(monkeypatch, handler):
    """Swaps `main_module.build_client` for one that always talks to
    an `httpx.MockTransport`, so command tests never touch the network."""
    from aios_dev_sdk import AiosDevClient

    def _build(config, *, transport=None):
        return AiosDevClient(config.base_url, api_key=(config.cli_token or config.api_key), transport=httpx.MockTransport(handler))

    monkeypatch.setattr(main_module, "build_client", _build)


def test_auth_login_stores_cli_token(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/cli/sessions"
        body = json.loads(request.content)
        assert body["api_key"] == "dpk_test"
        return httpx.Response(200, json={"cli_token": "cli_tok_123", "developer_id": "dev-1"})

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["auth", "login", "--base-url", "https://api.example.com", "--api-key", "dpk_test"])
    assert result.exit_code == 0, result.output
    assert "Logged in" in result.output

    config = load_config()
    assert config.cli_token == "cli_tok_123"
    assert config.developer_id == "dev-1"


def test_auth_whoami_shows_masked_token(monkeypatch):
    save_config(CliConfig(base_url="https://api.example.com", cli_token="cli_tok_abcdef", developer_id="dev-1"))
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["auth", "whoami"])
    assert result.exit_code == 0, result.output
    assert "...cdef" in result.output
    assert "cli_tok_abcdef" not in result.output


def test_auth_logout_clears_token():
    save_config(CliConfig(cli_token="cli_tok_1"))
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["auth", "logout"])
    assert result.exit_code == 0
    assert load_config().cli_token is None


def test_project_list_requires_auth():
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["project", "list"])
    assert result.exit_code != 0
    assert "not authenticated" in result.output


def test_project_list_paginates(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1"))

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(200, json={"items": [{"id": "p1", "name": "one", "status": "active"}], "total": 1, "page": 1, "page_size": 50})
        return httpx.Response(200, json={"items": [], "total": 1, "page": page, "page_size": 50})

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["project", "list"])
    assert result.exit_code == 0, result.output
    assert "one" in result.output


def test_project_create(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        return httpx.Response(200, json={"id": "p2", "name": "new-project", "status": "active"})

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["project", "create", "new-project"])
    assert result.exit_code == 0, result.output
    assert "new-project" in result.output


def test_deploy_command(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1"))

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body == {"resource_type": "agent", "resource_id": "agent-1", "strategy": "rolling"}
        return httpx.Response(200, json={"id": "deploy-1", "status": "in_progress"})

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["deploy", "agent", "agent-1"])
    assert result.exit_code == 0, result.output
    assert "deploy-1" in result.output


def test_logs_streams_events(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1"))

    def handler(request: httpx.Request) -> httpx.Response:
        body = "\n".join(json.dumps({"event": "log", "data": {"line": n}}) for n in range(3))
        return httpx.Response(200, content=body.encode())

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["logs", "deploy-1"])
    assert result.exit_code == 0, result.output
    assert result.output.count("[log]") == 3


def test_diagnostics_reports_connectivity_ok(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1"))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok"})

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["diagnostics"])
    assert result.exit_code == 0, result.output
    assert "connectivity" in result.output
    assert "ok" in result.output


def test_diagnostics_reports_connectivity_failure(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1"))

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["diagnostics"])
    assert result.exit_code == 0, result.output
    assert "unreachable" in result.output


def test_version_command():
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["version"])
    assert result.exit_code == 0
    assert "aios-cli" in result.output


def test_update_reports_newer_version_available(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"version": "2.0.0"})

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["update", "--check"])
    assert result.exit_code == 0, result.output
    assert "2.0.0" in result.output


def test_json_output_format(monkeypatch):
    save_config(CliConfig(cli_token="cli_tok_1", output_format="json"))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [{"id": "p1", "name": "one"}], "total": 1, "page": 1, "page_size": 50})

    _patch_client(monkeypatch, handler)
    runner = CliRunner()
    result = runner.invoke(main_module.cli, ["project", "list"])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.output)
    assert parsed[0]["id"] == "p1"
