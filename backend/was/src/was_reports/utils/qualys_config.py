"""Environment-backed Qualys configuration for WAS reporting."""

# Future Python Libraries
from __future__ import annotations

# Standard Python Libraries
from dataclasses import dataclass

# First-Party Libraries
from was_reports.utils.env import require_env


@dataclass(frozen=True)
class QualysCredentials:
    """Credential fields required for direct Qualys report downloads."""

    username: str
    password: str
    hostname: str


def load_qualys_credentials_from_environment() -> QualysCredentials:
    """Load Qualys credential fields from backend/was/.env or process env."""
    return QualysCredentials(
        username=require_env("WAS_QUALYS_USERNAME"),
        password=require_env("WAS_QUALYS_PASSWORD"),
        hostname=require_env("WAS_QUALYS_HOSTNAME"),
    )
