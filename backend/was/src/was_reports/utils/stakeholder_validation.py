"""Shared validation for WAS stakeholder records."""

# Standard Python Libraries
from datetime import date, datetime, timezone
from typing import Mapping


REQUIRED_STAKEHOLDER_FIELDS = frozenset(
    {"ci_type", "testing_sector", "frequency", "state"}
)
STAKEHOLDER_DATE_FIELDS = frozenset(
    {
        "web_apps_last_updated",
        "last_scanned",
        "next_scheduled",
        "onboarding_date",
    }
)
STAKEHOLDER_EMAIL_FIELDS = frozenset({"distro_email", "tech_poc_email"})


def validate_stakeholder_tag(value: object) -> str:
    """Return a nonempty stakeholder tag that contains no whitespace."""
    normalized_value = str(value).strip()
    if not normalized_value:
        raise ValueError("Stakeholder tag must not be empty.")
    if any(character.isspace() for character in normalized_value):
        raise ValueError("Stakeholder tag must not contain spaces or whitespace.")
    return normalized_value


def validate_email_value(value: object | None, field_name: str) -> object | None:
    """Reject line breaks in one stakeholder email field."""
    if value is not None and ("\r" in str(value) or "\n" in str(value)):
        raise ValueError("{} must not contain line breaks.".format(field_name))
    return value


def validate_required_fields(
    values: Mapping[str, object],
    *,
    require_all: bool,
) -> None:
    """Require configured stakeholder fields to be present and nonblank."""
    fields_to_check = REQUIRED_STAKEHOLDER_FIELDS
    if not require_all:
        fields_to_check = fields_to_check.intersection(values)
    for field_name in sorted(fields_to_check):
        value = values.get(field_name)
        if value is None or not str(value).strip():
            raise ValueError("{} must not be null or blank.".format(field_name))


def parse_stakeholder_date(value: str) -> int:
    """Return a nonnegative epoch from an epoch or exact YYYY-MM-DD input."""
    normalized_value = value.strip()
    try:
        parsed_epoch = int(normalized_value)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(normalized_value)
        except ValueError as error:
            raise ValueError(
                "Date must use YYYY-MM-DD format or be a nonnegative epoch."
            ) from error
        if parsed_date.isoformat() != normalized_value:
            raise ValueError(
                "Date must use YYYY-MM-DD format or be a nonnegative epoch."
            )
        return int(
            datetime.combine(parsed_date, datetime.min.time(), timezone.utc).timestamp()
        )
    if parsed_epoch < 0:
        raise ValueError("Date epoch must be zero or greater.")
    return parsed_epoch
