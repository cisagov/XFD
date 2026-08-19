#!/usr/bin/env python3
"""Invoke the local peAsmSyncController (start pe-asm-sync container)."""

# Standard Python Libraries
import argparse
import json
import sys

# Third-Party Libraries
from pe.peAsmSyncController import run


def main() -> int:
    """Parse CLI args and start local report generation."""
    parser = argparse.ArgumentParser(
        description="Start pe-asm-sync locally (Docker pe-worker)."
    )
    parser.add_argument(
        "--orgs",
        default="all",
        help="Comma-separated cyhy_db_name values or shortcut: all, demo, all-orgs, demo-orgs.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="Split resolved org list across N Fargate-style local containers.",
    )
    parser.add_argument(
        "--print-names",
        action="store_true",
        help="On success, print container names (one per line) to stdout.",
    )
    args = parser.parse_args()

    orgs = [org.strip() for org in args.orgs.split(",") if org.strip()]
    event = {
        "orgs": orgs,
        "taskCount": args.count,
        "local": True,
    }
    result = run(event)
    if result.get("statusCode") != 200:
        sys.stderr.write("{}\n".format(json.dumps(result, indent=2)))
        return 1

    body = json.loads(result["body"])
    if args.print_names:
        for name in body.get("containerNames", []):
            sys.stdout.write("{}\n".format(name))
        return 0

    sys.stdout.write("{}\n".format(json.dumps(result, indent=2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
