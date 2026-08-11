#!/usr/bin/env python3
"""Invoke the local peMailerController (start pe-mailer container)."""

# Standard Python Libraries
import argparse
import json
import sys

# Third-Party Libraries
from pe.peMailerController import run


def main() -> int:
    """Parse CLI args and start pe-mailer locally."""
    parser = argparse.ArgumentParser(
        description="Start pe-mailer locally (Docker pe-worker)."
    )
    parser.add_argument(
        "--orgs",
        default="all",
        help="Comma-separated cyhy_db_name values, or 'all'.",
    )
    parser.add_argument(
        "--summary-to",
        default="",
        help="Comma-separated email(s) for the end-of-run summary.",
    )
    parser.add_argument(
        "--test-emails",
        default="",
        help="Comma-separated email(s) to redirect report sends to, instead "
        "of real org contacts.",
    )
    parser.add_argument(
        "--print-name",
        action="store_true",
        help="On success, print the container name to stdout.",
    )
    args = parser.parse_args()

    event = {
        "orgs": args.orgs,
        "summaryTo": args.summary_to,
        "testEmails": args.test_emails,
        "local": True,
    }
    result = run(event)
    if result.get("statusCode") != 200:
        sys.stderr.write("{}\n".format(json.dumps(result, indent=2)))
        return 1

    body = json.loads(result["body"])
    if args.print_name:
        sys.stdout.write("{}\n".format(body.get("containerName", "")))
        return 0

    sys.stdout.write("{}\n".format(json.dumps(result, indent=2)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
