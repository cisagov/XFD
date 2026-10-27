"""CLI for listing Qualys WAS stakeholders and web application counts."""

# Standard Python Libraries
import argparse
from dataclasses import dataclass
import logging
import sys
from typing import List, Optional

# Third-Party Libraries
# First-Party Libraries
from was_reports.qualys.qualys_client import QualysClient, create_qualys_client
from was_reports.qualys.report_data import count_webapps, list_customer_tags
from was_reports.utils.logging_config import configure_logging

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class InventoryItem:
    """One WAS stakeholder inventory result."""

    tag: str
    description: str
    web_application_count: int


def get_inventory(client: QualysClient) -> List[InventoryItem]:
    """Return stakeholder tags, descriptions, and web application counts."""
    customer_tags = list_customer_tags(client)
    inventory = []
    for position, (tag, description) in enumerate(
        sorted(customer_tags.items()), start=1
    ):
        LOGGER.info(
            "Querying Qualys application count for %s (%s of %s).",
            tag,
            position,
            len(customer_tags),
        )
        inventory.append(
            InventoryItem(
                tag=tag,
                description=description,
                web_application_count=count_webapps(client, tag),
            )
        )
    return inventory


def print_inventory(inventory_items: List[InventoryItem]) -> None:
    """Print inventory in a stable operator-readable format."""
    sys.stdout.write("TAG\tDESCRIPTION\tWEB_APPLICATION_COUNT\n")
    for item in inventory_items:
        sys.stdout.write(
            "{}\t{}\t{}\n".format(
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
    configure_logging()
    parse_args(argv)
    client = create_qualys_client()
    print_inventory(get_inventory(client))
    return 0


if __name__ == "__main__":
    sys.exit(main())
