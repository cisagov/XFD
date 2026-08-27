"""Qualys configuration helpers for WAS report generation."""

# Standard Python Libraries
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

# First-Party Libraries
from was_reports.utils.env import getenv, require_env

REQUIRED_INFO_OPTIONS = ("username", "password", "hostname")
WAS_FILE_ENV_TO_CONFIG = {
    "WAS_DAILY_WAS_LOG": "dailywaslog",
}
DEFAULT_WAS_FILE_PATHS = {
    "WAS_DAILY_WAS_LOG": "WAS_Tools/update_tracker/dailywas.log",
}


@dataclass(frozen=True)
class QualysCredentials:
    """Credential fields required for direct Qualys report downloads."""

    username: str
    password: str
    hostname: str


def read_qualys_config(config_path: Path) -> ConfigParser:
    """Read the Qualys configuration file from disk."""
    if not config_path.is_file():
        raise FileNotFoundError(
            "WAS config file not found at {}.".format(str(config_path))
        )

    parser = ConfigParser()
    loaded_files = parser.read(config_path)
    if not loaded_files:
        raise ValueError(
            "WAS config file could not be read at {}.".format(str(config_path))
        )

    return parser


def missing_required_options(
    parser: ConfigParser,
    section_name: str,
    required_options: Iterable[str],
) -> list[str]:
    """Return required config options missing from a section."""
    missing_options = []
    if not parser.has_section(section_name):
        return list(required_options)

    for option_name in required_options:
        if not parser.has_option(section_name, option_name):
            missing_options.append(option_name)
        elif not parser.get(section_name, option_name).strip():
            missing_options.append(option_name)

    return missing_options


def validate_qualys_config(config_path: Path) -> None:
    """Validate required Qualys config fields without returning secrets."""
    parser = read_qualys_config(config_path)
    missing_options = missing_required_options(
        parser=parser,
        section_name="info",
        required_options=REQUIRED_INFO_OPTIONS,
    )

    if missing_options:
        raise ValueError(
            "WAS config file is missing required [info] option(s): {}.".format(
                ", ".join(missing_options)
            )
        )


def load_qualys_credentials_from_environment() -> QualysCredentials:
    """Load Qualys credential fields from backend/was/.env or process env."""
    return QualysCredentials(
        username=require_env("WAS_QUALYS_USERNAME"),
        password=require_env("WAS_QUALYS_PASSWORD"),
        hostname=require_env("WAS_QUALYS_HOSTNAME"),
    )


def write_qualys_config_file(
    config_path: Path,
    credentials: QualysCredentials,
    was_file_paths: Dict[str, str] | None = None,
) -> Path:
    """Write a legacy-compatible Qualys config file from environment values."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    parser = ConfigParser()
    parser["info"] = {
        "username": credentials.username,
        "password": credentials.password,
        "hostname": credentials.hostname,
    }
    if was_file_paths:
        parser["was_files"] = was_file_paths
    with config_path.open("w", encoding="utf-8") as config_file:
        parser.write(config_file)
    config_path.chmod(0o600)
    return config_path


def load_was_file_paths_from_environment() -> Dict[str, str]:
    """Load legacy WAS file path config values from environment constants."""
    was_file_paths: Dict[str, str] = {}
    share_drive = getenv("WAS_SHARE_DRIVE")
    for env_name, config_name in WAS_FILE_ENV_TO_CONFIG.items():
        value = getenv(env_name)
        if not value and share_drive:
            value = str(Path(share_drive) / DEFAULT_WAS_FILE_PATHS[env_name])
        if value:
            was_file_paths[config_name] = value
    return was_file_paths


def ensure_qualys_config_file(config_path: Path) -> Path:
    """Return a Qualys config path, creating it from .env when needed."""
    if config_path.is_file():
        return config_path

    credentials = load_qualys_credentials_from_environment()
    return write_qualys_config_file(
        config_path=config_path,
        credentials=credentials,
        was_file_paths=load_was_file_paths_from_environment(),
    )


def load_qualys_credentials(config_path: Path) -> QualysCredentials:
    """Load Qualys credential fields from a validated config file."""
    ensured_config_path = ensure_qualys_config_file(config_path)
    validate_qualys_config(ensured_config_path)
    parser = read_qualys_config(ensured_config_path)
    return QualysCredentials(
        username=parser.get("info", "username").strip(),
        password=parser.get("info", "password").strip(),
        hostname=parser.get("info", "hostname").strip(),
    )
