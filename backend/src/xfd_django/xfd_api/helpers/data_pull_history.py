"""Helper functions to fill data pull history table."""
# Standard Python Libraries
import datetime

# Third-Party Libraries
from xfd_mini_dl.models import DataPullTracker, Organization


def get_last_queried(org: Organization, data_source: str):
    """
    Retrieve the last time an organization queried a specific data source.

    Returns None if no record exists.
    """
    try:
        tracker = DataPullTracker.objects.using("mini_data_lake").get(
            org=org, data_source=data_source
        )
        return tracker.last_queried_at
    except DataPullTracker.DoesNotExist:
        return None  # No previous successful record found


def update_query_timestamp(org: Organization, data_source: str, query_time=None):
    """Update or create a query log entry when an organization successfully queries a data source."""
    if query_time is None:
        query_time = datetime.datetime.now(
            datetime.timezone.utc
        )  # Default to current timestamp

    tracker, created = DataPullTracker.objects.using("mini_data_lake").update_or_create(
        org=org,
        data_source=data_source,
        defaults={"last_queried_at": query_time},  # Always save successful queries
    )

    return created
