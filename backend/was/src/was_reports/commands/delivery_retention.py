"""Preview or apply the approved WAS delivery-review database retention rule."""

from __future__ import annotations

# Standard Python Libraries
import argparse

# Third-Party Libraries
from was_reports.data.delivery_retention import (
    apply_retention,
    retention_counts,
    retention_cutoff,
)


def main(argv: list[str] | None = None) -> int:
    """Report eligible row counts; apply expiry only with an explicit flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="delete expired retry detail and redact expired recipient copies",
    )
    arguments = parser.parse_args(argv)
    cutoff = retention_cutoff()
    counts = apply_retention(cutoff) if arguments.apply else retention_counts(cutoff)
    action = "Applied" if arguments.apply else "Preview"
    print(
        "{} 14-day delivery retention: {} retry rows, {} attempt recipient "
        "copies, {} SES event recipient copies.".format(
            action,
            counts["expired_retries"],
            counts["recipient_copies"],
            counts["event_recipient_copies"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
