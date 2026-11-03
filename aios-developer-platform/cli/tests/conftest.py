import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_cli_home(monkeypatch):
    """Every test gets its own config directory so tests never read or
    write a real developer's `~/.aios`."""
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("AIOS_CLI_HOME", tmp)
        yield tmp
