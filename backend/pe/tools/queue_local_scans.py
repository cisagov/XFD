#!/usr/bin/env python3
"""Invoke the local peScanController lambda (queue + Docker worker start)."""

# Standard Python Libraries
import argparse
import json
import sys
import textwrap

# Third-Party Libraries
from pe.peScanController import run

ORG_HELP_EPILOG = """
org shortcuts (use one shortcut alone — do not mix with named orgs)
  DHS,DHS_CISA
      One queue message per org. COUNT controls how many workers drain the queue.

  all, DEMO  — batch mode (one message, one worker job)
      One message is queued. The worker runs pe-source with --orgs=all or --orgs=DEMO
      and scans every report_on or demo org sequentially inside that single process.
      Use COUNT=1. Good for a simple local run.

  all-orgs, demo-orgs  — parallel mode (one message per org)
      peScanController queries the PE database and enqueues one message per
      cyhy_db_name. Set COUNT to the number of concurrent workers you want.
      Good when you need production-style parallelism across orgs.

examples
  %(prog)s --scans=dnstwist --orgs=DHS,DHS_CISA --count=2
  %(prog)s --scans=dnstwist --orgs=all --count=1
  %(prog)s --scans=dnstwist --orgs=all-orgs --count=3
"""


def main() -> int:
    """Parse CLI args and invoke the local peScanController workflow."""
    parser = argparse.ArgumentParser(
        description="Queue PE scan jobs locally (ElasticMQ + pe-worker).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(ORG_HELP_EPILOG),
    )
    parser.add_argument(
        "--scans",
        required=True,
        help="Comma-separated scan catalog keys (e.g. dnstwist).",
    )
    parser.add_argument(
        "--orgs",
        help=(
            "Comma-separated cyhy_db_name values (DHS,DHS_CISA), or one shortcut: "
            "all / DEMO (batch), all-orgs / demo-orgs (parallel)."
        ),
    )
    parser.add_argument(
        "--orgs-file",
        help="JSON file containing an array of organization names.",
    )
    parser.add_argument(
        "--count",
        type=int,
        metavar="N",
        help="Concurrent workers per scan (overrides catalog default).",
    )
    parser.add_argument(
        "--api-keys",
        default="",
        help="Comma-separated Shodan API keys.",
    )
    parser.add_argument(
        "--queue-only",
        action="store_true",
        help="Only queue messages; do not start workers.",
    )
    parser.add_argument(
        "--tasks-only",
        action="store_true",
        help="Only start workers; do not queue messages.",
    )
    args = parser.parse_args()

    scans = [scan.strip() for scan in args.scans.split(",") if scan.strip()]
    orgs = [org.strip() for org in (args.orgs or "").split(",") if org.strip()]

    if args.orgs_file:
        with open(args.orgs_file, encoding="utf-8") as org_file:
            orgs = json.load(org_file)

    if not args.tasks_only and not orgs:
        sys.stderr.write("Provide --orgs or --orgs-file.\n")
        return 1

    event = {
        "scans": scans,
        "orgs": orgs,
        "apiKeyList": args.api_keys,
        "queueOnly": args.queue_only,
        "tasksOnly": args.tasks_only,
        "local": True,
    }
    if args.count is not None:
        event["taskCount"] = args.count

    result = run(event)
    sys.stdout.write("{}\n".format(json.dumps(result, indent=2)))
    return 0 if result.get("statusCode") == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
