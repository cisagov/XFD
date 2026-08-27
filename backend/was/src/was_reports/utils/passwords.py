"""Password helpers for WAS PDF report encryption."""

# Standard Python Libraries
import secrets
import string
from typing import Iterable

# First-Party Libraries
from was_reports.utils.env import getenv

BANNED_PASSWORD_CHARACTERS = frozenset(["'", ",", "-"])
DEFAULT_PASSWORD_LENGTH = 24
MINIMUM_PASSWORD_LENGTH = 16
PASSWORD_CHARACTER_SET = "".join(
    character
    for character in string.ascii_letters + string.digits + string.punctuation
    if character not in BANNED_PASSWORD_CHARACTERS
)


def password_length_from_environment() -> int:
    """Return the configured WAS password length."""
    raw_length = getenv("WAS_PASSWORD_LENGTH")
    if not raw_length:
        return DEFAULT_PASSWORD_LENGTH

    try:
        password_length = int(raw_length)
    except ValueError as error:
        raise ValueError("WAS_PASSWORD_LENGTH must be an integer.") from error

    if password_length < MINIMUM_PASSWORD_LENGTH:
        raise ValueError(
            "WAS_PASSWORD_LENGTH must be at least {}.".format(MINIMUM_PASSWORD_LENGTH)
        )

    return password_length


def validate_report_password(value: str) -> None:
    """Validate that a report password follows WAS character rules."""
    if not value:
        raise ValueError("report_password must not be empty.")

    for character in value:
        if character not in PASSWORD_CHARACTER_SET:
            raise ValueError(
                "Character '{}' is not allowed in report_password.".format(character)
            )


def _contains_any(value: str, characters: Iterable[str]) -> bool:
    """Return whether a value contains at least one character from a collection."""
    for character in characters:
        if character in value:
            return True
    return False


def generate_report_password(length: int | None = None) -> str:
    """Generate a validated password for encrypting a WAS PDF report."""
    if length is not None:
        password_length = length
    else:
        password_length = password_length_from_environment()
    if password_length < MINIMUM_PASSWORD_LENGTH:
        raise ValueError(
            "Password length must be at least {}.".format(MINIMUM_PASSWORD_LENGTH)
        )

    while True:
        password = "".join(
            secrets.choice(PASSWORD_CHARACTER_SET) for _ in range(password_length)
        )
        if (
            _contains_any(password, string.ascii_lowercase)
            and _contains_any(password, string.ascii_uppercase)
            and _contains_any(password, string.digits)
            and _contains_any(password, string.punctuation)
        ):
            validate_report_password(password)
            return password
