"""Builds an `aios_dev_sdk` client from local CLI config. Kept as its
own tiny module (rather than inlined in every command) so tests can
monkeypatch a single seam — `build_client` — to inject an
`httpx.MockTransport` without touching every command function."""
from __future__ import annotations

from aios_dev_sdk import AiosDevClient

from aios_cli.config import CliConfig


def build_client(config: CliConfig, *, transport=None) -> AiosDevClient:
    token = config.cli_token or config.api_key
    return AiosDevClient(config.base_url, api_key=token, transport=transport)
