"""Local CLI configuration + credential storage. Lives at
`$AIOS_CLI_HOME/config.json` (defaults to `~/.aios`, overridable via
the `AIOS_CLI_HOME` env var so tests never touch a real home
directory). The CLI session token is stored here in plaintext, same
posture as `~/.aws/credentials` or `~/.netrc` — protecting it is the
filesystem permissions' job, not this file format's."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


def config_dir() -> Path:
    home = os.environ.get("AIOS_CLI_HOME")
    if home:
        return Path(home)
    return Path.home() / ".aios"


def config_path() -> Path:
    return config_dir() / "config.json"


@dataclass
class CliConfig:
    base_url: str = "http://localhost:8000"
    api_key: str | None = None
    cli_token: str | None = None
    developer_id: str | None = None
    output_format: str = "table"
    page_size: int = 50
    extra: dict = field(default_factory=dict)

    @property
    def is_authenticated(self) -> bool:
        return bool(self.cli_token)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CliConfig":
        known = {f for f in cls.__dataclass_fields__}
        base = {k: v for k, v in data.items() if k in known and k != "extra"}
        extra = {k: v for k, v in data.items() if k not in known}
        return cls(**base, extra=extra)


def load_config() -> CliConfig:
    path = config_path()
    if not path.exists():
        return CliConfig()
    try:
        return CliConfig.from_dict(json.loads(path.read_text()))
    except (json.JSONDecodeError, TypeError):
        return CliConfig()


def save_config(config: CliConfig) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = config.to_dict()
    extra = payload.pop("extra", {})
    payload.update(extra)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def set_field(key: str, value: str) -> CliConfig:
    config = load_config()
    if key in config.__dataclass_fields__ and key != "extra":
        if key == "page_size":
            value = int(value)  # type: ignore[assignment]
        setattr(config, key, value)
    else:
        config.extra[key] = value
    save_config(config)
    return config


def get_field(key: str) -> str | None:
    config = load_config()
    if key in config.__dataclass_fields__ and key != "extra":
        return getattr(config, key)
    return config.extra.get(key)


def clear_auth() -> CliConfig:
    config = load_config()
    config.cli_token = None
    config.api_key = None
    config.developer_id = None
    save_config(config)
    return config
