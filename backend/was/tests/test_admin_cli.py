"""Tests for the guarded Qualys WAS administration CLI."""

# Standard Python Libraries
import argparse
import unittest
from unittest.mock import Mock, call, patch

# Third-Party Libraries
# First-Party Libraries
from was_reports.commands import admin_cli
from was_reports.qualys.qualys_admin import WebAppIdentity


class AdminCliTests(unittest.TestCase):
    """Validate administration arguments, confirmation, and routing."""

    def test_rejects_mutation_without_confirmation(self) -> None:
        """Require explicit confirmation before changing Qualys state."""
        args = admin_cli.parse_args(
            [
                "add-tag",
                "--url",
                "https://example.gov",
                "--tag",
                "TAG1",
            ]
        )

        with self.assertRaisesRegex(ValueError, "requires --confirm"):
            admin_cli.execute_command(Mock(), args)

    def test_delete_requires_exact_url_confirmation(self) -> None:
        """Require the operator to repeat the exact deletion target URL."""
        args = admin_cli.parse_args(
            [
                "delete-webapp",
                "--url",
                "https://example.gov",
                "--confirm-url",
                "https://different.example.gov",
            ]
        )

        with self.assertRaisesRegex(ValueError, "exactly match"):
            admin_cli.execute_command(Mock(), args)

    def test_validated_delete_requires_exact_tag_confirmation(self) -> None:
        """Require the operator to repeat the expected deletion tag ID."""
        args = admin_cli.parse_args(
            [
                "delete-webapp-validated",
                "--url",
                "https://example.gov",
                "--expected-tag-id",
                "13396052",
                "--confirm-url",
                "https://example.gov",
                "--confirm-tag-id",
                "13396053",
            ]
        )

        with self.assertRaises(ValueError) as raised_error:
            admin_cli.execute_command(Mock(), args)
        self.assertIn("expected tag ID", str(raised_error.exception))

    def test_rejects_url_credentials(self) -> None:
        """Prevent credentials from being accepted as part of a target URL."""
        with self.assertRaises(argparse.ArgumentTypeError):
            admin_cli.validate_webapp_url("https://user:secret@example.gov")

    def test_rejects_invalid_tag_ids(self) -> None:
        """Accept only positive ASCII numeric Qualys tag IDs."""
        for value in ("0", "-1", "tag", "１２３"):
            with self.subTest(value=value), self.assertRaises(
                argparse.ArgumentTypeError
            ):
                admin_cli.validate_tag_id(value)

    @patch("was_reports.commands.admin_cli.delete_webapp")
    @patch("was_reports.commands.admin_cli.find_webapp_identity")
    def test_validated_delete_rechecks_identity_tag_and_stable_id(
        self,
        find_identity,
        delete,
    ) -> None:
        """Delete only after two stable reads confirm the sole expected test tag."""
        identity = WebAppIdentity(
            "42",
            "https://fakedomain.faketld",
            ("13396052",),
        )
        find_identity.side_effect = [identity, identity]
        client = Mock()
        args = admin_cli.parse_args(
            [
                "delete-webapp-validated",
                "--url",
                "https://fakedomain.faketld",
                "--expected-tag-id",
                "13396052",
                "--confirm-url",
                "https://fakedomain.faketld",
                "--confirm-tag-id",
                "13396052",
            ]
        )

        message = admin_cli.execute_command(client, args)

        self.assertIn("completed", message)
        self.assertEqual(
            find_identity.call_args_list,
            [
                call(client, "https://fakedomain.faketld"),
                call(client, "https://fakedomain.faketld"),
            ],
        )
        delete.assert_called_once_with(
            client,
            "https://fakedomain.faketld",
            webapp_id="42",
        )

    @patch("was_reports.commands.admin_cli.delete_webapp")
    @patch("was_reports.commands.admin_cli.find_webapp_identity")
    def test_validated_delete_blocks_changed_identity_or_tags(
        self,
        find_identity,
        delete,
    ) -> None:
        """Block deletion when identity changes or the tag set is unexpected."""
        expected = WebAppIdentity("42", "https://example.gov", ("13396052",))
        unsafe_responses = (
            (
                [
                    expected,
                    WebAppIdentity("43", "https://example.gov", ("13396052",)),
                ],
                "identity changed",
            ),
            (
                [
                    WebAppIdentity("42", "https://example.gov", ("999",)),
                    WebAppIdentity("42", "https://example.gov", ("999",)),
                ],
                "expected test tag",
            ),
            (
                [
                    WebAppIdentity(
                        "42",
                        "https://example.gov",
                        ("13396052", "999"),
                    ),
                    WebAppIdentity(
                        "42",
                        "https://example.gov",
                        ("13396052", "999"),
                    ),
                ],
                "additional tags",
            ),
        )
        args = admin_cli.parse_args(
            [
                "delete-webapp-validated",
                "--url",
                "https://example.gov",
                "--expected-tag-id",
                "13396052",
                "--confirm-url",
                "https://example.gov",
                "--confirm-tag-id",
                "13396052",
            ]
        )

        for responses, expected_message in unsafe_responses:
            with self.subTest(expected_message=expected_message):
                find_identity.reset_mock(side_effect=True)
                find_identity.side_effect = responses
                delete.reset_mock()
                with self.assertRaises(RuntimeError) as raised_error:
                    admin_cli.execute_command(Mock(), args)
                self.assertIn(expected_message, str(raised_error.exception))
                delete.assert_not_called()

    @patch("was_reports.commands.admin_cli.update_webapp_tag")
    @patch("was_reports.commands.admin_cli.get_tag_id")
    @patch("was_reports.commands.admin_cli.find_webapp_id")
    def test_add_tag_resolves_webapp_and_tag_ids(
        self,
        mock_find_webapp_id,
        mock_get_tag_id,
        mock_update_webapp_tag,
    ) -> None:
        """Resolve operator names before submitting a tag mutation."""
        client = Mock()
        mock_find_webapp_id.return_value = "42"
        mock_get_tag_id.return_value = "100"
        args = admin_cli.parse_args(
            [
                "add-tag",
                "--url",
                "https://example.gov",
                "--tag",
                "TAG1",
                "--confirm",
            ]
        )

        message = admin_cli.execute_command(client, args)

        self.assertIn("completed", message)
        mock_find_webapp_id.assert_called_once_with(client, "https://example.gov")
        mock_get_tag_id.assert_called_once_with(client, "TAG1")
        mock_update_webapp_tag.assert_called_once_with(
            client,
            "42",
            "100",
            "add",
        )

    @patch("was_reports.commands.admin_cli.reactivate_webapp")
    @patch("was_reports.commands.admin_cli.get_tag_id")
    def test_reactivate_resolves_each_repeated_tag(
        self,
        mock_get_tag_id,
        mock_reactivate_webapp,
    ) -> None:
        """Resolve every repeated tag before reactivating a web app."""
        client = Mock()
        mock_get_tag_id.side_effect = ["100", "200"]
        args = admin_cli.parse_args(
            [
                "reactivate",
                "--url",
                "https://example.gov",
                "--tag",
                "TAG1",
                "--tag",
                "TAG2",
                "--confirm",
            ]
        )

        admin_cli.execute_command(client, args)

        self.assertEqual(
            mock_get_tag_id.call_args_list,
            [call(client, "TAG1"), call(client, "TAG2")],
        )
        mock_reactivate_webapp.assert_called_once_with(
            client,
            "https://example.gov",
            ["100", "200"],
        )

    @patch("was_reports.commands.admin_cli.execute_command")
    @patch("was_reports.commands.admin_cli.create_qualys_client")
    def test_main_creates_environment_backed_qualys_client(
        self,
        mock_create_client,
        mock_execute_command,
    ) -> None:
        """Create the Qualys client directly from environment credentials."""
        mock_execute_command.return_value = "Completed."

        result = admin_cli.main(
            [
                "false-positive",
                "--finding-id",
                "123",
                "--comment",
                "Reviewed.",
                "--confirm",
            ]
        )

        self.assertEqual(result, 0)
        mock_create_client.assert_called_once_with()
        mock_execute_command.assert_called_once()

    @patch("was_reports.commands.admin_cli.create_qualys_client")
    def test_main_rejects_unconfirmed_operation_before_client_creation(
        self,
        mock_create_client,
    ) -> None:
        """Do not connect to Qualys when confirmation is missing."""
        result = admin_cli.main(
            [
                "add-tag",
                "--url",
                "https://example.gov",
                "--tag",
                "TAG1",
            ]
        )

        self.assertEqual(result, 2)
        mock_create_client.assert_not_called()
        mock_create_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
