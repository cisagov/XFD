"""CLI wrapper for running the WAS daily tracker update."""

# Standard Python Libraries
import argparse
import sys
from typing import List, Optional

# First-Party Libraries
from was_reports.qualys.qualys_client import create_qualys_client
from was_reports.tracker.qualys_scans import DEFAULT_TRACKER_LOOKBACK_DAYS
from was_reports.tracker.service import refresh_daily_tracker
from was_reports.utils.logging_config import configure_logging


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
) -> None:
    """Run the WAS-owned Qualys-to-Postgres tracker workflow."""
    refresh_daily_tracker(
        client=create_qualys_client(),
        delete_apps=delete_apps,
        stakeholder_tag=stakeholder_tag,
        tracker_lookback_days=tracker_lookback_days,
        preflight_only=preflight_only,
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
