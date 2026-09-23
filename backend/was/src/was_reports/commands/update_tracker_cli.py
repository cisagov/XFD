"""CLI wrapper for running the WAS daily tracker update."""

# Standard Python Libraries
import argparse
import logging
import os
import sys
from time import monotonic
from typing import List, Optional

# First-Party Libraries
from was_reports.qualys.qualys_client import create_qualys_client
from was_reports.tracker.qualys_scans import DEFAULT_TRACKER_LOOKBACK_DAYS
from was_reports.tracker.service import refresh_daily_tracker
from was_reports.utils.logging_config import configure_logging


class TrackerErrorCounter(logging.Handler):
    """Count tracker errors without retaining sensitive log messages."""

    def __init__(self) -> None:
        """Observe only errors emitted during this tracker operation."""
        super().__init__(logging.ERROR)
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Keep only an aggregate count, never formatted log content."""
        self.count += 1


def positive_day_count(value: str) -> int:
    """Return a positive number of days for an argparse option."""
    day_count = int(value)
    if day_count < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return day_count


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse WAS update tracker CLI arguments."""
    parser = argparse.ArgumentParser(
        description=("Run the WAS daily tracker update from Qualys into Postgres."),
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Count discovered pending runs without enrichment or database updates.",
    )
    parser.add_argument(
        "--delete-apps",
        action="store_true",
        help=(
            "Delete Qualys webapps identified by the NWS removal workflow. "
            "The default is non-destructive."
        ),
    )
    parser.add_argument(
        "-t",
        "--tag",
        help=(
            "Process only the exact stakeholder tag after discovering recent "
            "Qualys schedules."
        ),
    )
    parser.add_argument(
        "--lookback-days",
        dest="tracker_lookback_days",
        type=positive_day_count,
        default=DEFAULT_TRACKER_LOOKBACK_DAYS,
        help=(
            "Search for Qualys schedules from this many days before the "
            "latest tracker update. Defaults to 3."
        ),
    )
    return parser.parse_args(argv)


def run_update_tracker(
    delete_apps: bool,
    stakeholder_tag: Optional[str] = None,
    tracker_lookback_days: int = DEFAULT_TRACKER_LOOKBACK_DAYS,
    preflight_only: bool = False,
    analyst_batch_id: str | None = None,
    summary_enabled: bool = True,
) -> None:
    """Run the WAS-owned Qualys-to-Postgres tracker workflow."""
    batch_id = None if preflight_only or not summary_enabled else (
        analyst_batch_id or os.environ.get("WAS_ANALYST_BATCH_ID")
    )
    started = monotonic()
    error_name = None
    rows_updated = None
    error_counter = TrackerErrorCounter()
    tracker_logger = logging.getLogger("was_reports.tracker")
    if batch_id:
        from was_reports.reporting import analyst_summaries

        analyst_summaries.start_batch(batch_id)
        tracker_logger.addHandler(error_counter)
    try:
        rows_updated = refresh_daily_tracker(
            client=create_qualys_client(),
            delete_apps=delete_apps,
            stakeholder_tag=stakeholder_tag,
            tracker_lookback_days=tracker_lookback_days,
            preflight_only=preflight_only,
        )
    except Exception as error:
        error_name = type(error).__name__
        raise
    finally:
        if batch_id:
            tracker_logger.removeHandler(error_counter)
            if error_name is None and error_counter.count:
                error_name = "TrackerLoggedErrors_{}".format(error_counter.count)
            analyst_summaries.record_tracker_result(
                batch_id, monotonic() - started, error=error_name, rows_updated=rows_updated
            )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS update tracker CLI."""
    configure_logging()
    args = parse_args(argv)
    stakeholder_tag = args.tag.strip() if args.tag else None
    if args.tag and not stakeholder_tag:
        raise ValueError("Stakeholder tag must not be empty.")
    run_update_tracker(
        delete_apps=args.delete_apps,
        stakeholder_tag=stakeholder_tag,
        tracker_lookback_days=args.tracker_lookback_days,
        preflight_only=args.preflight_only,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
