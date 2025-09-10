"""Task datetime utils."""

# Standard Python Libraries
import datetime
from datetime import timedelta
from datetime import timezone as dt_timezone
import logging
import os

# Third-Party Libraries
from dateutil import parser  # type: ignore
from django.utils import timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    filename="vuln_scanning_sync.log",
)
LOGGER = logging.getLogger(__name__)
IS_LOCAL = os.getenv("IS_LOCAL")


def to_utc_naive(dt):
    """Convert aware -> UTC naive for Redshift TIMESTAMP parameters."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(dt_timezone.utc).replace(tzinfo=None)


def safe_fromisoformat(date_input) -> datetime.datetime | None:
    """Safely convert input to timezone-aware datetime, or return None if invalid."""
    if isinstance(date_input, datetime.datetime):
        return (
            timezone.make_aware(date_input)
            if timezone.is_naive(date_input)
            else date_input
        )
    if isinstance(date_input, str):
        try:
            parsed = parser.parse(date_input)
            return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
        except Exception as e:
            LOGGER.warning(
                "Failed to parse datetime from string: %s | Error: %s", date_input, e
            )
            return None
    return None


def freeze_window(days_back: int = 2):
    """Freeze [start, end) from two days ago at midnight to last night at midnight UTC."""
    now = timezone.now().astimezone(dt_timezone.utc)
    # Last night midnight UTC
    end_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # Start date = midnight 'days_back' days before end_dt
    start_dt = end_dt - timedelta(days=days_back)
    return start_dt, end_dt


def safe_parse_date(date_str):
    """
    Safely parse a date string into a datetime object (UTC).

    Args:
        date_str (str): The date string to parse.

    Returns:
        datetime.datetime or None: Parsed datetime in UTC, or None if invalid.
    """
    if not date_str:
        return None
    try:
        dt = parser.isoparse(date_str)  # parses ISO 8601 and other common formats
        if dt.tzinfo is None:
            # Assume naive datetime is UTC
            return dt
        else:
            # Convert to UTC
            return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None
