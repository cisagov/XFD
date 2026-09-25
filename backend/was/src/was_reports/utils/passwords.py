"""Password helpers for WAS PDF report encryption."""

# Standard Python Libraries
import secrets
import string
from typing import Iterable

# First-Party Libraries
from was_reports.utils.env import getenv

BANNED_PASSWORD_CHARACTERS = frozenset([",", "-"])
DEFAULT_PASSWORD_LENGTH = 24
MINIMUM_PASSWORD_LENGTH = 16
CUSTOMER_PASSWORD_REQUIREMENTS = (
    "at least 16 characters with an uppercase letter, lowercase letter, "
    "number, and special character; spaces, commas, and hyphens are not allowed"
)
PASSWORD_CHARACTER_SET = "".join(
    character
    for character in string.ascii_letters + string.digits + string.punctuation
    if character not in BANNED_PASSWORD_CHARACTERS
)
EXISTING_PASSWORD_CHARACTER_SET = PASSWORD_CHARACTER_SET + ",- "


class ExistingReportPasswordError(ValueError):
    """Indicate that a stored report password cannot be used safely."""


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


def _validate_password_characters(value: str, allowed_characters: str) -> None:
    """Require a nonempty password containing only the supplied characters."""
    if not value:
        raise ValueError("report_password must not be empty.")

    for character in value:
        if character not in allowed_characters:
            raise ValueError(
                "report_password contains an unsupported character."
            )


def validate_report_password(value: str) -> None:
    """Validate that a new report password follows WAS character rules."""
    _validate_password_characters(value, PASSWORD_CHARACTER_SET)


def validate_existing_report_password(value: str) -> None:
    """Accept existing printable ASCII passwords without stripping literal spaces."""
    try:
        _validate_password_characters(value, EXISTING_PASSWORD_CHARACTER_SET)
    except ValueError as error:
        raise ExistingReportPasswordError(
            "Stored report password is empty or contains an unsupported character."
        ) from error


def _contains_any(value: str, characters: Iterable[str]) -> bool:
    """Return whether a value contains at least one character from a collection."""
    for character in characters:
        if character in value:
            return True
    return False


def validate_customer_provided_report_password(value: str) -> None:
    """Validate a customer password against the complete WAS password policy."""
    validate_report_password(value)
    if len(value) < MINIMUM_PASSWORD_LENGTH:
        raise ValueError(
            "The password must contain at least {} characters.".format(
                MINIMUM_PASSWORD_LENGTH
            )
        )
    required_character_classes = (
        (string.ascii_lowercase, "a lowercase letter"),
        (string.ascii_uppercase, "an uppercase letter"),
        (string.digits, "a number"),
        (string.punctuation, "a special character"),
    )
    for characters, description in required_character_classes:
        if not _contains_any(value, characters):
            raise ValueError("The password must contain {}.".format(description))


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
