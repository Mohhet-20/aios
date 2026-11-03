from aios_cli.config import CliConfig, clear_auth, config_path, get_field, load_config, save_config, set_field


def test_load_config_defaults_when_missing():
    config = load_config()
    assert config.base_url == "http://localhost:8000"
    assert config.cli_token is None


def test_save_and_load_round_trip():
    config = CliConfig(base_url="https://api.example.com", api_key="dpk_abc", output_format="json")
    save_config(config)
    assert config_path().exists()

    loaded = load_config()
    assert loaded.base_url == "https://api.example.com"
    assert loaded.api_key == "dpk_abc"
    assert loaded.output_format == "json"


def test_set_and_get_field_known_key():
    set_field("base_url", "https://custom.example.com")
    assert get_field("base_url") == "https://custom.example.com"


def test_set_and_get_field_extra_key():
    set_field("favorite_color", "blue")
    assert get_field("favorite_color") == "blue"
    assert get_field("unknown_key") is None


def test_clear_auth_removes_credentials_but_keeps_base_url():
    config = CliConfig(base_url="https://api.example.com", api_key="dpk_abc", cli_token="tok_1", developer_id="dev-1")
    save_config(config)

    cleared = clear_auth()
    assert cleared.base_url == "https://api.example.com"
    assert cleared.api_key is None
    assert cleared.cli_token is None
    assert cleared.developer_id is None
