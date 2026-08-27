"""Tests for the WAS stakeholder inventory command."""

# Standard Python Libraries
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, call, patch

# First-Party Libraries
from was_reports.commands import inventory_cli


class InventoryCliTests(unittest.TestCase):
    """Validate inventory collection and operator output."""

    @patch("was_reports.commands.inventory_cli.count_webapps")
    @patch("was_reports.commands.inventory_cli.list_customer_tags")
    def test_get_inventory_sorts_tags_and_counts_webapps(
        self,
        mock_list_tags,
        mock_count_webapps,
    ) -> None:
        """Return stable inventory rows with one count request per tag."""
        mock_list_tags.return_value = {
            "TAG_B": "Agency B",
            "TAG_A": "Agency A",
        }
        mock_count_webapps.side_effect = [3, 7]
        client = Mock()

        inventory = inventory_cli.get_inventory(client)

        self.assertEqual(
            inventory,
            [
                inventory_cli.InventoryItem("TAG_A", "Agency A", 3),
                inventory_cli.InventoryItem("TAG_B", "Agency B", 7),
            ],
        )
        self.assertEqual(
            mock_count_webapps.call_args_list,
            [call(client, "TAG_A"), call(client, "TAG_B")],
        )

    def test_print_inventory_uses_stable_tabular_output(self) -> None:
        """Print a header and one row per stakeholder tag."""
        output = io.StringIO()

        with redirect_stdout(output):
            inventory_cli.print_inventory(
                [inventory_cli.InventoryItem("TAG_A", "Agency A", 3)]
            )

        self.assertEqual(
            output.getvalue(),
            "TAG\tDESCRIPTION\tWEB_APPLICATION_COUNT\n"
            "TAG_A\tAgency A\t3\n",
        )

    @patch("was_reports.commands.inventory_cli.print_inventory")
    @patch("was_reports.commands.inventory_cli.get_inventory")
    @patch("was_reports.commands.inventory_cli.create_qualys_client")
    @patch("was_reports.commands.inventory_cli.prepare_legacy_config")
    def test_main_prepares_config_and_prints_inventory(
        self,
        mock_prepare_config,
        mock_create_client,
        mock_get_inventory,
        mock_print_inventory,
    ) -> None:
        """Create the Qualys client only after preparing its configuration."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        mock_get_inventory.return_value = []

        result = inventory_cli.main(["--config-path", "/tmp/was_config.txt"])

        self.assertEqual(result, 0)
        mock_prepare_config.assert_called_once()
        mock_create_client.assert_called_once()
        mock_get_inventory.assert_called_once_with(mock_client)
        mock_print_inventory.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()
