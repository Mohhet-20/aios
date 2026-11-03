import pytest
from pydantic import ValidationError

from identity_platform.config.settings import DEV_SECRET_KEY, Settings


def test_production_refuses_the_development_signing_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(app_env="production", secret_key=DEV_SECRET_KEY)


def test_production_refuses_a_short_signing_key():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(app_env="production", secret_key="too-short")


def test_production_accepts_a_strong_private_key():
    assert Settings(app_env="production", secret_key="k" * 48).is_production


def test_development_keeps_the_default_for_local_runs(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)  # the suite's conftest sets one
    assert Settings(app_env="development", _env_file=None).secret_key == DEV_SECRET_KEY
