"""CLI wrapper for running the WAS daily tracker update."""

# Standard Python Libraries
import argparse
import sys
from typing import List, Optional

# First-Party Libraries
from was_reports.qualys.qualys_client import create_qualys_client
from was_reports.tracker.service import refresh_daily_tracker


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse WAS update tracker CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the WAS daily tracker update from Qualys into Postgres."
        ),
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
    return parser.parse_args(argv)


def run_update_tracker(
    delete_apps: bool,
    stakeholder_tag: Optional[str] = None,
) -> None:
    """Run the WAS-owned Qualys-to-Postgres tracker workflow."""
    refresh_daily_tracker(
        client=create_qualys_client(),
        delete_apps=delete_apps,
        stakeholder_tag=stakeholder_tag,
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS update tracker CLI."""
    args = parse_args(argv)
    stakeholder_tag = args.tag.strip() if args.tag else None
    if args.tag and not stakeholder_tag:
        raise ValueError("Stakeholder tag must not be empty.")
    run_update_tracker(
        delete_apps=args.delete_apps,
        stakeholder_tag=stakeholder_tag,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
