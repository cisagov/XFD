"""CLI for listing Qualys WAS stakeholders and web application counts."""

# Standard Python Libraries
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# First-Party Libraries
from was_reports.qualys_client import QualysClient, create_qualys_client
from was_reports.report_data import count_webapps, list_customer_tags
from was_reports.report_generator import prepare_legacy_config
from was_reports.utils.env import getenv


@dataclass(frozen=True)
class InventoryItem:
    """One WAS stakeholder inventory result."""

    tag: str
    description: str
    web_application_count: int


def get_inventory(client: QualysClient) -> List[InventoryItem]:
    """Return stakeholder tags, descriptions, and web application counts."""
    customer_tags = list_customer_tags(client)
    return [
        InventoryItem(
            tag=tag,
            description=description,
            web_application_count=count_webapps(client, tag),
        )
        for tag, description in sorted(customer_tags.items())
    ]


def print_inventory(inventory_items: List[InventoryItem]) -> None:
    """Print inventory in a stable operator-readable format."""
    print("TAG\tDESCRIPTION\tWEB_APPLICATION_COUNT")
    for item in inventory_items:
        print(
            "{}\t{}\t{}".format(
                item.tag,
                item.description,
                item.web_application_count,
            )
        )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse stakeholder inventory command-line arguments."""
    parser = argparse.ArgumentParser(
        description="List Qualys WAS stakeholders and web application counts."
    )
    parser.add_argument(
        "--config-path",
        default=getenv(
            "WAS_CONFIG_PATH",
            "/WAS_REPORT_GENERATION/docs/was_config.txt",
        ),
        help="Path to the generated Qualys configuration file.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS stakeholder inventory command."""
    args = parse_args(argv)
    config_path = Path(args.config_path)
    prepare_legacy_config(config_path)
    client = create_qualys_client(config_path)
    print_inventory(get_inventory(client))
    return 0


if __name__ == "__main__":
    sys.exit(main())
