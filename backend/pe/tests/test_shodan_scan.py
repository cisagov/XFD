"""Unit tests for Shodan script orchestration behavior."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import MagicMock, patch
import uuid

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
from pe_source.shodan.shodan_script import Get_shodan


class ShodanScriptTests(unittest.TestCase):
    """Verify Shodan script org filtering, sorting, and thread wiring."""

    def setUp(self):
        """Build reusable org fixtures with mixed flags and unsorted names."""
        self.org_uid_1 = str(uuid.uuid4())
        self.org_uid_2 = str(uuid.uuid4())
        self.org_uid_3 = str(uuid.uuid4())
        self.org_uid_4 = str(uuid.uuid4())
        self.mock_all_orgs = [
            {
                "organizations_uid": self.org_uid_1,
                "cyhy_db_name": "org_c",
                "report_on": True,
                "demo": False,
            },
            {
                "organizations_uid": self.org_uid_2,
                "cyhy_db_name": "org_a",
                "report_on": False,
                "demo": True,
            },
            {
                "organizations_uid": self.org_uid_3,
                "cyhy_db_name": "org_b",
                "report_on": True,
                "demo": False,
            },
            {
                "organizations_uid": self.org_uid_4,
                "cyhy_db_name": "org_demo2",
                "report_on": False,
                "demo": True,
            },
        ]

    @patch("pe_source.shodan.shodan_script.threading.Thread")
    @patch("pe_source.shodan.shodan_script.shodan_api_init")
    @patch("pe_source.shodan.shodan_script.get_orgs")
    def test_run_shodan_all_filters_and_sorts_orgs(
        self, mock_get_orgs, mock_shodan_api_init, mock_thread
    ):
        """All should include report_on orgs only and dispatch in sorted order."""
        mock_get_orgs.return_value = self.mock_all_orgs
        api_client = object()
        mock_shodan_api_init.return_value = [api_client]
        created_thread = MagicMock()
        mock_thread.return_value = created_thread

        Get_shodan("all").run_shodan()

        mock_get_orgs.assert_called_once()
        mock_shodan_api_init.assert_called_once()
        mock_thread.assert_called_once()
        args = mock_thread.call_args.kwargs["args"]
        self.assertIs(args[0], api_client)
        # Sorted order should be org_b then org_c for report_on=True fixtures.
        self.assertEqual(
            [org["cyhy_db_name"] for org in list(args[1])], ["org_b", "org_c"]
        )
        self.assertEqual(args[2], "Thread 1:")
        created_thread.start.assert_called_once()
        created_thread.join.assert_called_once()

    @patch("pe_source.shodan.shodan_script.threading.Thread")
    @patch("pe_source.shodan.shodan_script.shodan_api_init")
    @patch("pe_source.shodan.shodan_script.get_orgs")
    def test_run_shodan_demo_filters_demo_orgs(
        self, mock_get_orgs, mock_shodan_api_init, mock_thread
    ):
        """DEMO should include demo orgs only and dispatch in sorted order."""
        mock_get_orgs.return_value = self.mock_all_orgs
        api_client = object()
        mock_shodan_api_init.return_value = [api_client]
        created_thread = MagicMock()
        mock_thread.return_value = created_thread

        Get_shodan("DEMO").run_shodan()

        args = mock_thread.call_args.kwargs["args"]
        self.assertEqual(
            [org["cyhy_db_name"] for org in list(args[1])],
            ["org_a", "org_demo2"],
        )
        created_thread.start.assert_called_once()
        created_thread.join.assert_called_once()

    @patch("pe_source.shodan.shodan_script.threading.Thread")
    @patch("pe_source.shodan.shodan_script.shodan_api_init")
    @patch("pe_source.shodan.shodan_script.get_orgs")
    def test_run_shodan_comma_string_filters_exact_org_names(
        self, mock_get_orgs, mock_shodan_api_init, mock_thread
    ):
        """Comma-separated input should split and match exact cyhy_db_name values."""
        mock_get_orgs.return_value = self.mock_all_orgs
        api_client = object()
        mock_shodan_api_init.return_value = [api_client]
        created_thread = MagicMock()
        mock_thread.return_value = created_thread

        Get_shodan(" org_c, org_a ").run_shodan()

        args = mock_thread.call_args.kwargs["args"]
        self.assertEqual(
            [org["cyhy_db_name"] for org in list(args[1])], ["org_a", "org_c"]
        )

    @patch("pe_source.shodan.shodan_script.threading.Thread")
    @patch("pe_source.shodan.shodan_script.shodan_api_init")
    @patch("pe_source.shodan.shodan_script.get_orgs")
    def test_run_shodan_iterable_filters_exact_org_names(
        self, mock_get_orgs, mock_shodan_api_init, mock_thread
    ):
        """Iterable input should match exact names and preserve sorted dispatch."""
        mock_get_orgs.return_value = self.mock_all_orgs
        api_client = object()
        mock_shodan_api_init.return_value = [api_client]
        created_thread = MagicMock()
        mock_thread.return_value = created_thread

        Get_shodan(["org_b", "org_a"]).run_shodan()

        args = mock_thread.call_args.kwargs["args"]
        self.assertEqual(
            [org["cyhy_db_name"] for org in list(args[1])], ["org_a", "org_b"]
        )

    @patch("pe_source.shodan.shodan_script.threading.Thread")
    @patch("pe_source.shodan.shodan_script.shodan_api_init")
    @patch("pe_source.shodan.shodan_script.get_orgs")
    def test_run_shodan_creates_one_thread_per_api_client(
        self, mock_get_orgs, mock_shodan_api_init, mock_thread
    ):
        """Thread count should match API client count and use numbered names."""
        mock_get_orgs.return_value = self.mock_all_orgs
        api_client_1 = object()
        api_client_2 = object()
        mock_shodan_api_init.return_value = [api_client_1, api_client_2]
        thread_1 = MagicMock()
        thread_2 = MagicMock()
        mock_thread.side_effect = [thread_1, thread_2]

        Get_shodan("all").run_shodan()

        self.assertEqual(mock_thread.call_count, 2)
        first_args = mock_thread.call_args_list[0].kwargs["args"]
        second_args = mock_thread.call_args_list[1].kwargs["args"]
        self.assertIs(first_args[0], api_client_1)
        self.assertIs(second_args[0], api_client_2)
        self.assertEqual(first_args[2], "Thread 1:")
        self.assertEqual(second_args[2], "Thread 2:")
        thread_1.start.assert_called_once()
        thread_2.start.assert_called_once()
        thread_1.join.assert_called_once()
        thread_2.join.assert_called_once()

    @patch("pe_source.shodan.shodan_script.threading.Thread")
    @patch("pe_source.shodan.shodan_script.shodan_api_init")
    @patch("pe_source.shodan.shodan_script.get_orgs")
    def test_run_shodan_handles_empty_selected_orgs(
        self, mock_get_orgs, mock_shodan_api_init, mock_thread
    ):
        """No matching orgs should still safely initialize and run one empty chunk."""
        mock_get_orgs.return_value = self.mock_all_orgs
        api_client = object()
        mock_shodan_api_init.return_value = [api_client]
        created_thread = MagicMock()
        mock_thread.return_value = created_thread

        Get_shodan("does_not_exist").run_shodan()

        mock_thread.assert_called_once()
        args = mock_thread.call_args.kwargs["args"]
        self.assertEqual(list(args[1]), [])
        created_thread.start.assert_called_once()
        created_thread.join.assert_called_once()


if __name__ == "__main__":
    unittest.main()
