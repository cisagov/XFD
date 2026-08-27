"""CLI for managing WAS special cases."""

# Standard Python Libraries
import argparse
import sys
from typing import List, Optional

# First-Party Libraries
from was_reports.data.special_cases import (
    deactivate_special_case,
    list_special_cases,
    upsert_special_case,
)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse WAS special case CLI arguments."""
    parser = argparse.ArgumentParser(description="Manage WAS special cases.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    list_command = subcommands.add_parser("list", help="List special cases.")
    list_command.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive special cases.",
    )

    add_command = subcommands.add_parser("add", help="Add or reactivate a case.")
    add_command.add_argument("value", help="Special case value, such as CROSSFEED.")

    remove_command = subcommands.add_parser("remove", help="Deactivate a case.")
    remove_command.add_argument(
        "value",
        help="Special case value to deactivate, such as CROSSFEED.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS special case CLI."""
    args = parse_args(argv)

    from was_reports.utils.database import close, connect

    conn = connect()
    try:
        if args.command == "list":
            cases = list_special_cases(
                conn=conn,
                include_inactive=args.include_inactive,
            )
            for special_case in cases:
                print(
                    "{},{},{}".format(
                        special_case.id,
                        special_case.value,
                        special_case.active,
                    )
                )
            return 0

        if args.command == "add":
            special_case = upsert_special_case(
                value=args.value,
                conn=conn,
            )
            print(
                "Added special case {}.".format(
                    special_case.value,
                )
            )
            return 0

        changed = deactivate_special_case(
            value=args.value,
            conn=conn,
        )
        if changed:
            print("Deactivated special case {}.".format(args.value.upper()))
        else:
            print("No active special case found for {}.".format(args.value.upper()))
        return 0
    finally:
        close(conn)


if __name__ == "__main__":
    sys.exit(main())
