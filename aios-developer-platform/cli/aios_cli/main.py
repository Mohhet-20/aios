"""`aios` — the official AIOS Enterprise Developer Platform CLI.
Every network-touching command builds its HTTP client via
`client_factory.build_client`, which tests monkeypatch to inject a
mock transport — so this whole command tree is exercised in the test
suite without a live server."""
from __future__ import annotations

import platform
import time

import click

import aios_dev_sdk
from aios_dev_sdk import AiosApiError, AiosSdkError

from aios_cli import __version__
from aios_cli.client_factory import build_client
from aios_cli.config import CliConfig, clear_auth, get_field, load_config, save_config, set_field
from aios_cli.output import render, render_one


def _fail(message: str) -> None:
    raise click.ClickException(message)


def _handle_sdk_error(exc: AiosSdkError) -> None:
    if isinstance(exc, AiosApiError):
        _fail(f"API error ({exc.status_code}): {exc}")
    _fail(f"connection error: {exc}")


def _require_auth(config: CliConfig) -> None:
    if not config.is_authenticated:
        _fail("not authenticated — run `aios auth login` first")


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """AIOS Enterprise Developer Platform CLI."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config()


# -- auth ---------------------------------------------------------------------------------------

@cli.group()
def auth() -> None:
    """Authenticate the CLI against an AIOS deployment."""


@auth.command("login")
@click.option("--base-url", required=True, help="Base URL of the AIOS Developer Platform API.")
@click.option("--api-key", required=True, help="A raw API key issued via the API Platform.")
@click.pass_context
def auth_login(ctx: click.Context, base_url: str, api_key: str) -> None:
    """Exchange an API key for a CLI session and store it locally."""
    config: CliConfig = ctx.obj["config"]
    config.base_url = base_url
    config.api_key = api_key
    client = build_client(config)
    try:
        response = client.request("POST", "/v1/cli/sessions", json={"api_key": api_key})
    except AiosSdkError as exc:
        _handle_sdk_error(exc)
        return
    finally:
        client.close()

    body = response.json()
    config.cli_token = body.get("cli_token", api_key)
    config.developer_id = body.get("developer_id")
    save_config(config)
    click.echo(f"Logged in to {base_url}")


@auth.command("logout")
def auth_logout() -> None:
    """Clear the locally stored session."""
    clear_auth()
    click.echo("Logged out.")


@auth.command("whoami")
@click.pass_context
def auth_whoami(ctx: click.Context) -> None:
    config: CliConfig = ctx.obj["config"]
    masked = f"...{config.cli_token[-4:]}" if config.cli_token else None
    render_one(
        {"base_url": config.base_url, "developer_id": config.developer_id, "authenticated": config.is_authenticated, "token": masked},
        fmt=config.output_format,
    )


# -- config ---------------------------------------------------------------------------------------

@cli.group("config")
def config_group() -> None:
    """Read and write local CLI configuration."""


@config_group.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    value = get_field(key)
    click.echo(value if value is not None else "")


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    set_field(key, value)
    click.echo(f"{key} = {value}")


@config_group.command("list")
@click.pass_context
def config_list(ctx: click.Context) -> None:
    config: CliConfig = ctx.obj["config"]
    data = config.to_dict()
    data.pop("api_key", None)
    data.pop("cli_token", None)
    render_one(data, fmt=config.output_format)


# -- generic resource helper ------------------------------------------------------------------------

def _resource_group(name: str, path: str, item_columns: list[str]):
    @cli.group(name)
    def group() -> None:  # noqa: ANN202 — click decorator boilerplate
        pass

    @group.command("list")
    @click.pass_context
    def list_cmd(ctx: click.Context) -> None:
        config: CliConfig = ctx.obj["config"]
        _require_auth(config)
        client = build_client(config)
        try:
            items = list(client.paginate(path, item_factory=lambda d: d, page_size=config.page_size))
        except AiosSdkError as exc:
            _handle_sdk_error(exc)
            return
        finally:
            client.close()
        render(items, fmt=config.output_format, columns=item_columns)

    @group.command("create")
    @click.argument("name")
    @click.pass_context
    def create_cmd(ctx: click.Context, name: str) -> None:
        config: CliConfig = ctx.obj["config"]
        _require_auth(config)
        client = build_client(config)
        try:
            response = client.request("POST", path, json={"name": name})
        except AiosSdkError as exc:
            _handle_sdk_error(exc)
            return
        finally:
            client.close()
        render_one(response.json(), fmt=config.output_format)

    return group


project = _resource_group("project", "/v1/projects", ["id", "name", "status"])
workspace_group = _resource_group("workspace", "/v1/workspaces", ["id", "name"])
agent = _resource_group("agent", "/v1/agents", ["id", "name", "status"])
workflow = _resource_group("workflow", "/v1/workflows", ["id", "name", "status"])
prompt = _resource_group("prompt", "/v1/prompts", ["id", "name", "status"])
plugin = _resource_group("plugin", "/v1/plugins", ["id", "name", "category"])


@plugin.command("install")
@click.argument("name")
@click.option("--version", "plugin_version", default=None, help="Specific version to install; defaults to latest.")
@click.pass_context
def plugin_install(ctx: click.Context, name: str, plugin_version: str | None) -> None:
    config: CliConfig = ctx.obj["config"]
    _require_auth(config)
    client = build_client(config)
    try:
        response = client.request("POST", f"/v1/plugins/{name}/install", json={"version": plugin_version})
    except AiosSdkError as exc:
        _handle_sdk_error(exc)
        return
    finally:
        client.close()
    render_one(response.json(), fmt=config.output_format)


# -- deploy / logs / monitor -------------------------------------------------------------------------

@cli.command("deploy")
@click.argument("resource_type")
@click.argument("resource_id")
@click.option("--strategy", default="rolling", help="Deployment strategy: rolling, blue_green, canary, shadow.")
@click.pass_context
def deploy(ctx: click.Context, resource_type: str, resource_id: str, strategy: str) -> None:
    config: CliConfig = ctx.obj["config"]
    _require_auth(config)
    client = build_client(config)
    try:
        response = client.request(
            "POST", "/v1/deployments", json={"resource_type": resource_type, "resource_id": resource_id, "strategy": strategy}
        )
    except AiosSdkError as exc:
        _handle_sdk_error(exc)
        return
    finally:
        client.close()
    render_one(response.json(), fmt=config.output_format)


@cli.command("logs")
@click.argument("deployment_id")
@click.pass_context
def logs(ctx: click.Context, deployment_id: str) -> None:
    config: CliConfig = ctx.obj["config"]
    _require_auth(config)
    client = build_client(config)
    try:
        for event in client.stream(f"/v1/deployments/{deployment_id}/logs"):
            click.echo(f"[{event.event_type}] {event.data}")
    except AiosSdkError as exc:
        _handle_sdk_error(exc)
    finally:
        client.close()


@cli.command("monitor")
@click.pass_context
def monitor(ctx: click.Context) -> None:
    config: CliConfig = ctx.obj["config"]
    _require_auth(config)
    client = build_client(config)
    try:
        response = client.request("GET", "/v1/observability/summary")
    except AiosSdkError as exc:
        _handle_sdk_error(exc)
        return
    finally:
        client.close()
    render_one(response.json(), fmt=config.output_format)


# -- diagnostics / update / version -----------------------------------------------------------------

@cli.command("diagnostics")
@click.pass_context
def diagnostics(ctx: click.Context) -> None:
    config: CliConfig = ctx.obj["config"]
    report = {
        "cli_version": __version__,
        "sdk_version": aios_dev_sdk.__version__,
        "python_version": platform.python_version(),
        "base_url": config.base_url,
        "authenticated": config.is_authenticated,
    }
    client = build_client(config)
    started = time.monotonic()
    try:
        client.request("GET", "/health")
        report["connectivity"] = "ok"
        report["latency_ms"] = round((time.monotonic() - started) * 1000, 2)
    except AiosSdkError as exc:
        report["connectivity"] = f"unreachable ({exc})"
    finally:
        client.close()
    render_one(report, fmt=config.output_format)


@cli.command("update")
@click.option("--check", is_flag=True, default=False, help="Only check for a newer version; don't install.")
@click.pass_context
def update(ctx: click.Context, check: bool) -> None:
    config: CliConfig = ctx.obj["config"]
    client = build_client(config)
    try:
        response = client.request("GET", "/v1/registry/packages/aios-cli/versions/latest")
        latest = response.json().get("version")
    except AiosSdkError as exc:
        _handle_sdk_error(exc)
        return
    finally:
        client.close()

    if latest and latest != __version__:
        click.echo(f"A newer version is available: {latest} (installed: {__version__})")
        if not check:
            click.echo("Run `pip install --upgrade aios-cli` to update.")
    else:
        click.echo(f"Already up to date ({__version__}).")


@cli.command("version")
def version_cmd() -> None:
    click.echo(f"aios-cli {__version__} (aios-dev-sdk {aios_dev_sdk.__version__})")


if __name__ == "__main__":
    cli()
