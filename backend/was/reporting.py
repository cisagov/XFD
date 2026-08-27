#!/usr/bin/env python3
"""Compatibility entrypoint for scheduled WAS report generation.

The legacy implementation in this file read the daily tracker workbook,
started nested Docker containers, and retrieved static passwords from
DynamoDB. The containerized WAS path now uses Postgres scheduling and delegates
to `was_reports.commands.batch_runner`.
"""

# Standard Python Libraries
import sys
from typing import List, Optional

# First-Party Libraries
from was_reports.commands.batch_runner import main as batch_main


def main(argv: Optional[List[str]] = None) -> int:
    """Run scheduled WAS report generation through the new batch runner."""
    return batch_main(argv)


if __name__ == "__main__":
    sys.exit(main())
