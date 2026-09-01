"""CLI for listing Qualys WAS stakeholders and web application counts."""

# Standard Python Libraries
import argparse
import sys
from dataclasses import dataclass
from typing import List, Optional

# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, create_qualys_client
from was_reports.qualys.report_data import count_webapps, list_customer_tags


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
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the WAS stakeholder inventory command."""
    parse_args(argv)
    client = create_qualys_client()
    print_inventory(get_inventory(client))
    return 0


if __name__ == "__main__":
    sys.exit(main())
