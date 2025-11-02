"""Helper methods to deal with date and time manipulation."""
# Standard Python Libraries
import datetime


def calculate_days_back(days_ago_int: int):
    """Create a date string of a calculated past date."""
    # Step 1: Get the current date and time in UTC
    current_time = datetime.datetime.now(datetime.timezone.utc)
    # Step 2: Subtract days from the current date
    days_ago = current_time - datetime.timedelta(days=days_ago_int)
    # Step 3: Convert to an ISO 8601 string with timezone (e.g., UTC)
    since_timestamp_str = days_ago.isoformat()

    return since_timestamp_str
