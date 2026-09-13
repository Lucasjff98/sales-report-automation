"""
Unit tests for delivery.config: load_delivery_settings,
load_credentials_from_env, and build_email_config.

Run with:
    pytest tests/test_config.py -v
"""

import json
from pathlib import Path

import pytest
import yaml

from delivery.config import (
    build_email_config,
    load_credentials_from_env,
    load_delivery_settings,
)


@pytest.fixture
def valid_settings_dict() -> dict:
    return {
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "recipients": ["boss@example.com", "finance@example.com"],
    }


# ---------------------------------------------------------------------------
# load_delivery_settings (non-sensitive, file-based)
# ---------------------------------------------------------------------------

def test_loads_valid_yaml_settings(tmp_path: Path, valid_settings_dict):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(valid_settings_dict))

    result = load_delivery_settings(config_path)

    assert result["smtp_host"] == "smtp.office365.com"
    assert result["recipients"] == ["boss@example.com", "finance@example.com"]


def test_loads_valid_json_settings(tmp_path: Path, valid_settings_dict):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(valid_settings_dict))

    result = load_delivery_settings(config_path)

    assert result["smtp_port"] == 587


def test_settings_do_not_require_credentials(tmp_path: Path, valid_settings_dict):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(valid_settings_dict))

    result = load_delivery_settings(config_path)

    assert "sender_email" not in result
    assert "sender_password" not in result


def test_defaults_use_tls_to_true_when_absent(tmp_path: Path, valid_settings_dict):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(valid_settings_dict))

    result = load_delivery_settings(config_path)

    assert result["use_tls"] is True


def test_respects_explicit_use_tls_false(tmp_path: Path, valid_settings_dict):
    valid_settings_dict["use_tls"] = False
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(valid_settings_dict))

    result = load_delivery_settings(config_path)

    assert result["use_tls"] is False


def test_settings_raises_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_delivery_settings(tmp_path / "does_not_exist.yaml")


def test_settings_raises_value_error_for_unsupported_extension(tmp_path: Path):
    bad_path = tmp_path / "config.txt"
    bad_path.write_text("smtp_host: smtp.office365.com")

    with pytest.raises(ValueError, match="Unsupported config extension"):
        load_delivery_settings(bad_path)


def test_settings_raises_value_error_when_required_key_missing(
    tmp_path: Path, valid_settings_dict
):
    del valid_settings_dict["smtp_port"]
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(valid_settings_dict))

    with pytest.raises(ValueError, match="Missing required config key"):
        load_delivery_settings(config_path)


def test_settings_raises_value_error_when_recipients_empty(
    tmp_path: Path, valid_settings_dict
):
    valid_settings_dict["recipients"] = []
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(valid_settings_dict))

    with pytest.raises(ValueError, match="recipients"):
        load_delivery_settings(config_path)


def test_settings_raises_value_error_when_content_is_not_a_mapping(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(["not", "a", "mapping"]))

    with pytest.raises(ValueError, match="top-level object/mapping"):
        load_delivery_settings(config_path)


# ---------------------------------------------------------------------------
# load_credentials_from_env (sensitive, .env-based)
# ---------------------------------------------------------------------------

def test_loads_credentials_from_env_file(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "SENDER_EMAIL=reports@example.com\nSENDER_PASSWORD=app-password-123\n"
    )

    result = load_credentials_from_env(env_path)

    assert result == {
        "sender_email": "reports@example.com",
        "sender_password": "app-password-123",
    }


def test_credentials_raises_value_error_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("SENDER_EMAIL", raising=False)
    monkeypatch.delenv("SENDER_PASSWORD", raising=False)

    empty_env_path = tmp_path / ".env"
    empty_env_path.write_text("")

    with pytest.raises(ValueError, match="Missing required environment variable"):
        load_credentials_from_env(empty_env_path)


def test_credentials_raises_when_only_one_var_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("SENDER_EMAIL", raising=False)
    monkeypatch.delenv("SENDER_PASSWORD", raising=False)

    env_path = tmp_path / ".env"
    env_path.write_text("SENDER_EMAIL=reports@example.com\n")

    with pytest.raises(ValueError, match="SENDER_PASSWORD"):
        load_credentials_from_env(env_path)


# ---------------------------------------------------------------------------
# build_email_config (merges both sources)
# ---------------------------------------------------------------------------

def test_build_email_config_merges_settings_and_credentials(
    tmp_path: Path, valid_settings_dict
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(valid_settings_dict))

    env_path = tmp_path / ".env"
    env_path.write_text(
        "SENDER_EMAIL=reports@example.com\nSENDER_PASSWORD=app-password-123\n"
    )

    result = build_email_config(config_path, env_path)

    assert result == {
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "recipients": ["boss@example.com", "finance@example.com"],
        "use_tls": True,
        "sender_email": "reports@example.com",
        "sender_password": "app-password-123",
    }