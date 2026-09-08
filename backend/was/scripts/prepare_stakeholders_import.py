#!/usr/bin/env python3
"""Prepare a WAS stakeholder CSV for database import."""

# First-Party Libraries
from was_reports.commands.stakeholder_import import main


if __name__ == "__main__":
    raise SystemExit(main())
