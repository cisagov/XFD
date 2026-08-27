"""Environment loading helpers for WAS runtime configuration."""

# Standard Python Libraries
import os
from pathlib import Path
from typing import Optional


def was_root() -> Path:
    """Return the backend/was project root."""
    return Path(__file__).resolve().parents[3]


def default_env_path() -> Path:
    """Return the default local WAS environment file path."""
    return was_root() / ".env"


def clean_env_value(raw_value: str) -> str:
    """Remove simple wrapping quotes from an environment value."""
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_env_file(
    env_path: Optional[Path] = None,
    override: bool = False,
) -> None:
    """Load key-value pairs from a local .env file into process environment."""
    resolved_path = env_path or default_env_path()
    if not resolved_path.is_file():
        return

    for raw_line in resolved_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        name = key.strip()
        if not name:
            continue
        if not override and os.environ.get(name):
            continue
        os.environ[name] = clean_env_value(raw_value)


def getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return an environment variable after loading backend/was/.env."""
    load_env_file()
    return os.environ.get(name, default)


def require_env(name: str) -> str:
    """Return a required environment variable after loading backend/was/.env."""
    value = getenv(name)
    if not value:
        raise RuntimeError("Missing required environment variable: {}".format(name))
    return value
