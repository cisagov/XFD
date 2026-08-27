"""CLI wrapper for running the WAS daily tracker update."""

# Standard Python Libraries
import argparse
import sys
from pathlib import Path
from typing import List, Optional

UPDATE_TRACKER_ROOT = (
    Path(__file__).resolve().parents[2] / "update_tracker" / "update_tracker"
)


def ensure_update_tracker_path() -> None:
    """Add the legacy update tracker package directory to the import path."""
    path_value = str(UPDATE_TRACKER_ROOT)
    if path_value not in sys.path:
        sys.path.insert(0, path_value)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse WAS update tracker CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run the WAS daily tracker update from Qualys into Postgres.",
    )
    parser.add_argument(
        "--delete-apps",
        action="store_true",
        help=(
            "Delete Qualys webapps identified by the NWS removal workflow. "
            "The default is non-destructive."
        ),
    )
    return parser.parse_args(argv)


def run_update_tracker(delete_apps: bool) -> None:
    """Run the legacy update tracker workflow."""
    ensure_update_tracker_path()

    # First-Party Libraries
    from main import main as update_tracker_main

    update_tracker_main(delete_apps=delete_apps)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS update tracker CLI."""
    args = parse_args(argv)
    run_update_tracker(delete_apps=args.delete_apps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
