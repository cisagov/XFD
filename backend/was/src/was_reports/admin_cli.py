"""Guarded CLI for mutating Qualys WAS resources."""

# Standard Python Libraries
import argparse
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlsplit

# First-Party Libraries
from was_reports.qualys_admin import (
    delete_webapp,
    find_webapp_id,
    mark_false_positive,
    reactivate_webapp,
    update_webapp_tag,
)
from was_reports.qualys_client import QualysClient, create_qualys_client
from was_reports.report_data import get_tag_id
from was_reports.report_generator import prepare_legacy_config
from was_reports.utils.env import getenv


def validate_webapp_url(value: str) -> str:
    """Validate an absolute HTTP or HTTPS web application URL."""
    normalized_value = value.strip()
    parsed_url = urlsplit(normalized_value)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise argparse.ArgumentTypeError(
            "Web application URL must be an absolute HTTP or HTTPS URL."
        )
    if parsed_url.username or parsed_url.password:
        raise argparse.ArgumentTypeError(
            "Web application URL must not contain credentials."
        )
    return normalized_value


def validate_nonempty(value: str) -> str:
    """Return a stripped nonempty command-line value."""
    normalized_value = value.strip()
    if not normalized_value:
        raise argparse.ArgumentTypeError("Value must not be empty.")
    return normalized_value


def validate_finding_id(value: str) -> str:
    """Validate a positive numeric Qualys finding ID."""
    normalized_value = value.strip()
    if not normalized_value.isdecimal() or int(normalized_value) < 1:
        raise argparse.ArgumentTypeError(
            "Finding ID must be a positive numeric value."
        )
    return normalized_value


def require_confirmation(args: argparse.Namespace) -> None:
    """Reject a mutation unless the operator explicitly confirms it."""
    if args.command == "delete-webapp":
        if args.confirm_url != args.url:
            raise ValueError(
                "Deletion confirmation must exactly match the web application URL."
            )
        return
    if not args.confirm:
        raise ValueError("This Qualys mutation requires --confirm.")


def execute_command(client: QualysClient, args: argparse.Namespace) -> str:
    """Execute one validated Qualys administration command."""
    require_confirmation(args)

    if args.command in {"add-tag", "remove-tag"}:
        webapp_id = find_webapp_id(client, args.url)
        tag_id = get_tag_id(client, args.tag)
        action = "add" if args.command == "add-tag" else "remove"
        update_webapp_tag(client, webapp_id, tag_id, action)
        return "Qualys web application tag update completed."

    if args.command == "false-positive":
        mark_false_positive(client, args.finding_id, args.comment)
        return "Qualys finding was marked as a false positive."

    if args.command == "reactivate":
        tag_ids = [get_tag_id(client, tag_name) for tag_name in args.tag]
        reactivate_webapp(client, args.url, tag_ids)
        return "Qualys web application reactivation completed."

    if args.command == "delete-webapp":
        delete_webapp(client, args.url)
        return "Qualys web application deletion completed."

    raise ValueError("Unsupported administration command.")


def add_common_mutation_confirmation(parser: argparse.ArgumentParser) -> None:
    """Add the explicit mutation confirmation option to a subcommand."""
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that the requested Qualys mutation should be performed.",
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse Qualys WAS administration command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Perform guarded Qualys WAS administration operations."
    )
    parser.add_argument(
        "--config-path",
        default=getenv(
            "WAS_CONFIG_PATH",
            "/WAS_REPORT_GENERATION/docs/was_config.txt",
        ),
        help="Path to the generated Qualys configuration file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command_name in ("add-tag", "remove-tag"):
        tag_parser = subparsers.add_parser(command_name)
        tag_parser.add_argument("--url", required=True, type=validate_webapp_url)
        tag_parser.add_argument("--tag", required=True, type=validate_nonempty)
        add_common_mutation_confirmation(tag_parser)

    false_positive_parser = subparsers.add_parser("false-positive")
    false_positive_parser.add_argument(
        "--finding-id",
        required=True,
        type=validate_finding_id,
    )
    false_positive_parser.add_argument(
        "--comment",
        required=True,
        type=validate_nonempty,
    )
    add_common_mutation_confirmation(false_positive_parser)

    reactivate_parser = subparsers.add_parser("reactivate")
    reactivate_parser.add_argument(
        "--url",
        required=True,
        type=validate_webapp_url,
    )
    reactivate_parser.add_argument(
        "--tag",
        required=True,
        action="append",
        type=validate_nonempty,
        help="Qualys tag to set. Repeat this option for additional tags.",
    )
    add_common_mutation_confirmation(reactivate_parser)

    delete_parser = subparsers.add_parser("delete-webapp")
    delete_parser.add_argument(
        "--url",
        required=True,
        type=validate_webapp_url,
    )
    delete_parser.add_argument(
        "--confirm-url",
        required=True,
        type=validate_webapp_url,
        help="Repeat the exact URL to confirm permanent deletion.",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run one guarded Qualys WAS administration operation."""
    args = parse_args(argv)
    try:
        require_confirmation(args)
    except ValueError as error:
        print("Error: {}".format(str(error)), file=sys.stderr)
        return 2

    config_path = Path(args.config_path)
    prepare_legacy_config(config_path)
    client = create_qualys_client(config_path)
    try:
        print(execute_command(client, args))
    except (LookupError, RuntimeError, ValueError) as error:
        print("Error: {}".format(str(error)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
