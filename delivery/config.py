"""
Delivery module: load email delivery configuration from two sources:

1. Environment variables (.env file): SENSITIVE credentials only.
       SENDER_EMAIL     - the "from" address and SMTP login
       SENDER_PASSWORD  - account password or app password

2. A YAML or JSON config file: NON-sensitive settings only.
       smtp_host   : str, e.g. "smtp.office365.com"
       smtp_port   : int, e.g. 587
       recipients  : list[str], one or more "to" addresses
       use_tls     : bool, optional, defaults to True

SECURITY NOTE: only the .env file contains secrets, so it's the only
file that must never be committed to version control (it should be
listed in .gitignore). The YAML/JSON config file contains no sensitive
data and can safely be committed, since it holds only server/recipient
settings, not credentials.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

REQUIRED_SETTINGS_KEYS = ("smtp_host", "smtp_port", "recipients")
REQUIRED_ENV_KEYS = ("SENDER_EMAIL", "SENDER_PASSWORD")

YAML_EXTENSIONS = {".yaml", ".yml"}
JSON_EXTENSIONS = {".json"}


def load_delivery_settings(config_path: str | Path) -> dict[str, Any]:
    """
    Load and validate NON-sensitive delivery settings from a YAML/JSON file.

    Parameters
    ----------
    config_path : str | Path
        Path to the .yaml, .yml, or .json config file.

    Returns
    -------
    dict[str, Any]
        Parsed settings: smtp_host, smtp_port, recipients, use_tls
        (defaults to True if absent).

    Raises
    ------
    FileNotFoundError
        If config_path does not exist.
    ValueError
        If the file extension is unsupported, the content is not a
        mapping/object, a required key is missing, or "recipients" is
        empty.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Delivery settings file not found: {path}")

    extension = path.suffix.lower()
    raw_text = path.read_text(encoding="utf-8")

    if extension in YAML_EXTENSIONS:
        settings = yaml.safe_load(raw_text)
    elif extension in JSON_EXTENSIONS:
        settings = json.loads(raw_text)
    else:
        raise ValueError(
            f"Unsupported config extension '{extension}'. "
            f"Expected one of: {YAML_EXTENSIONS | JSON_EXTENSIONS}"
        )

    if not isinstance(settings, dict):
        raise ValueError("Config file must contain a top-level object/mapping.")

    missing = [key for key in REQUIRED_SETTINGS_KEYS if key not in settings]
    if missing:
        raise ValueError(f"Missing required config key(s): {missing}")

    if not settings["recipients"]:
        raise ValueError(
            "Config key 'recipients' must contain at least one address."
        )

    settings.setdefault("use_tls", True)

    return settings


def load_credentials_from_env(env_path: str | Path | None = None) -> dict[str, str]:
    """
    Load SENSITIVE credentials from environment variables, optionally
    loading them first from a .env file.

    Parameters
    ----------
    env_path : str | Path, optional
        Path to a .env file to load before reading the environment.
        If omitted, python-dotenv's default discovery is used (it
        searches the current and parent directories for a ".env" file).

    Returns
    -------
    dict[str, str]
        sender_email, sender_password.

    Raises
    ------
    ValueError
        If SENDER_EMAIL or SENDER_PASSWORD is not set.
    """
    if env_path is not None:
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    missing = [key for key in REQUIRED_ENV_KEYS if not os.environ.get(key)]
    if missing:
        raise ValueError(
            f"Missing required environment variable(s): {missing}. "
            "Set them in your .env file or shell environment."
        )

    return {
        "sender_email": os.environ["SENDER_EMAIL"],
        "sender_password": os.environ["SENDER_PASSWORD"],
    }


def build_email_config(
    config_path: str | Path, env_path: str | Path | None = None
) -> dict[str, Any]:
    """
    Combine non-sensitive settings (file) and credentials (environment)
    into a single config dict, in the shape expected by
    delivery.email_sender.send_report_email.

    Parameters
    ----------
    config_path : str | Path
        Path to the YAML/JSON file with smtp_host, smtp_port,
        recipients, and optionally use_tls.
    env_path : str | Path, optional
        Path to a .env file with SENDER_EMAIL and SENDER_PASSWORD.
        If omitted, python-dotenv's default discovery is used.

    Returns
    -------
    dict[str, Any]
        Merged config: smtp_host, smtp_port, sender_email,
        sender_password, recipients, use_tls.
    """
    settings = load_delivery_settings(config_path)
    credentials = load_credentials_from_env(env_path)
    return {**settings, **credentials}