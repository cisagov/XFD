"""Standalone reports must not enroll customers or alter daily tracking."""

from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from was_reports.commands import standalone_cli
from was_reports.data import standalone_targets
from was_reports.data.report_runs import ActiveReportOperationError
from was_mailer.message import recipient_addresses
from was_mailer import email_reports
from was_reports.qualys.report_data import parse_tag_details


class StandaloneTargetsTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value.__enter__.return_value
        self.stack.enter_context(
            patch.object(standalone_targets, "connect", return_value=self.conn)
        )
        self.stack.enter_context(patch.object(standalone_targets, "close"))
        self.stack.enter_context(
            patch.object(
                standalone_targets,
                "normalized_recipient",
                side_effect=lambda v: v.lower(),
            )
        )
        self.stack.enter_context(
            patch.object(
                standalone_targets,
                "generate_report_password",
                return_value="Generated!234",
            )
        )

    def test_new_target_and_run_do_not_insert_stakeholder_or_tracker(self):
        self.cursor.fetchone.side_effect = [None, None, (7,), None, (9,)]
        result = standalone_targets.create_standalone_request(
            "TEST", 123, "Analyst@example.gov"
        )
        self.assertEqual(result.run.id, 9)
        self.assertEqual(result.password, "Generated!234")
        statements = "\n".join(c.args[0] for c in self.cursor.execute.call_args_list)
        self.assertIn("INSERT INTO was_standalone_report_targets", statements)
        self.assertNotIn("INSERT INTO was_stakeholders", statements)
        self.assertNotIn("was_daily_report_tracker", statements)
        self.conn.commit.assert_called_once()

    def test_existing_password_preserved_exactly_without_update(self):
        password = '  "Exact,Password"  '
        self.cursor.fetchone.side_effect = [
            None,
            (7, "TEST", password, "analyst@example.gov"),
            None,
            (10,),
        ]
        result = standalone_targets.create_standalone_request("TEST", 123, None)
        self.assertEqual(result.password, password)
        self.assertNotIn(password, repr(result))
        statements = "\n".join(c.args[0] for c in self.cursor.execute.call_args_list)
        self.assertNotIn("UPDATE was_standalone_report_targets", statements)

    def test_enrolled_tag_rejected(self):
        self.cursor.fetchone.return_value = (1,)
        with self.assertRaisesRegex(ValueError, "enrolled"):
            standalone_targets.create_standalone_request("TEST", 123, None)
        self.conn.rollback.assert_called_once()
        self.conn.commit.assert_not_called()

    def test_recipient_change_rejected(self):
        self.cursor.fetchone.side_effect = [
            None,
            (7, "TEST", "secret", "old@example.gov"),
        ]
        with self.assertRaisesRegex(ValueError, "differs"):
            standalone_targets.create_standalone_request("TEST", 123, "new@example.gov")
        self.conn.commit.assert_not_called()

    def test_active_run_rejected(self):
        self.cursor.fetchone.side_effect = [
            None,
            (7, "TEST", "secret", "old@example.gov"),
            (9,),
        ]
        with self.assertRaises(ActiveReportOperationError):
            standalone_targets.create_standalone_request("TEST", 123, None)
        self.conn.commit.assert_not_called()

    def test_new_target_requires_recipient(self):
        self.cursor.fetchone.side_effect = [None, None]
        with self.assertRaisesRegex(ValueError, "required"):
            standalone_targets.create_standalone_request("TEST", 123, None)
        self.conn.commit.assert_not_called()


class StandaloneCommandTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.services = {}
        for name in (
            "require_env",
            "create_qualys_client",
            "load_qualys_credentials_from_environment",
            "get_tag_details",
            "create_standalone_request",
            "generate_report_output",
            "complete_report_run_by_id",
            "fail_report_run_by_id",
            "touch_report_run_by_id",
            "send_report_run_email",
        ):
            self.services[name] = self.stack.enter_context(
                patch.object(standalone_cli, name)
            )
        self.services["get_tag_details"].return_value = SimpleNamespace(
            name="TEST", tag_id="123", description="Test"
        )
        self.services["create_standalone_request"].return_value = SimpleNamespace(
            run=SimpleNamespace(id=9, generation_token="token"),
            password="exact secret",
            delivery_email="a@example.gov",
        )
        self.services["generate_report_output"].return_value = "s3://test/report.pdf"
        self.args = SimpleNamespace(
            tag="TEST",
            send_email=True,
            delivery_email="a@example.gov",
            resource_root="/tmp",
            staging_directory="/tmp",
        )

    def test_generation_uses_stored_secret_not_command_line_and_standalone_delivery(
        self,
    ):
        standalone_cli.run_standalone(self.args)
        options = self.services["generate_report_output"].call_args.kwargs
        self.assertEqual(options["password_override"], "exact secret")
        self.assertFalse(options["allow_tag_lookup"])
        self.assertFalse(options["create_missing_password"])
        self.assertEqual(
            self.services["send_report_run_email"].call_args.kwargs["delivery_purpose"],
            "standalone",
        )

    def test_archive_only_does_not_send(self):
        self.args.send_email = False
        standalone_cli.run_standalone(self.args)
        self.services["send_report_run_email"].assert_not_called()

    def test_generation_failure_records_failure_without_email(self):
        self.services["generate_report_output"].side_effect = RuntimeError("failure")
        with self.assertRaises(RuntimeError):
            standalone_cli.run_standalone(self.args)
        self.services["fail_report_run_by_id"].assert_called_once()
        self.services["send_report_run_email"].assert_not_called()

    def test_completion_failure_does_not_mark_uploaded_artifact_failed(self):
        self.services["complete_report_run_by_id"].side_effect = RuntimeError("failure")
        with self.assertRaises(RuntimeError):
            standalone_cli.run_standalone(self.args)
        self.services["fail_report_run_by_id"].assert_not_called()
        self.services["send_report_run_email"].assert_not_called()

    def test_wrong_qualys_name_does_not_create_target(self):
        self.services["get_tag_details"].return_value.name = "OTHER"
        with self.assertRaises(ValueError):
            standalone_cli.run_standalone(self.args)
        self.services["create_standalone_request"].assert_not_called()


class StandaloneEmailRetryTests(unittest.TestCase):
    """Explicit standalone retries must preserve uncertain-delivery holds."""

    def test_standalone_claim_excludes_held_even_with_failed_retries(self):
        """Exercise CLI through the atomic claim without contacting DB or SES."""
        for include_previous_failures in (False, True):
            with self.subTest(include_previous_failures=include_previous_failures):
                connection = MagicMock()
                cursor = connection.cursor.return_value.__enter__.return_value
                # PostgreSQL returns no row when a held run fails the predicate.
                cursor.fetchone.return_value = None
                arguments = [
                    "--report-run-id", "9",
                    "--source-email", "sender@example.gov",
                    "--delivery-purpose", "standalone",
                ]
                if include_previous_failures:
                    arguments.append("--include-previous-failures")
                with ExitStack() as stack:
                    stack.enter_context(patch.object(email_reports, "configure_logging"))
                    stack.enter_context(patch.object(
                        email_reports, "recover_stale_report_operations_in_db"
                    ))
                    stack.enter_context(patch(
                        "was_reports.utils.database.connect", return_value=connection
                    ))
                    stack.enter_context(patch("was_reports.utils.database.close"))
                    create_client = stack.enter_context(patch.object(
                        email_reports, "create_ses_client"
                    ))
                    send_message = stack.enter_context(patch.object(
                        email_reports, "send_message"
                    ))
                    with self.assertRaisesRegex(RuntimeError, "not available"):
                        email_reports.main(arguments)
                    create_client.assert_not_called()
                    send_message.assert_not_called()
                cursor.execute.assert_called_once()
                statement, parameters = cursor.execute.call_args.args
                self.assertIn("COALESCE(email_status, %s) = ANY(%s)", statement)
                self.assertIn("AND delivery_purpose = %s", statement)
                expected_statuses = ["pending"]
                if include_previous_failures:
                    expected_statuses.append("failed")
                self.assertEqual(parameters[-2], expected_statuses)
                self.assertEqual(parameters[-1], "standalone")
                connection.commit.assert_called_once()

    def test_other_explicit_delivery_purposes_keep_held_retry_policy(self):
        """Retain customer and analyst explicit held-run retry behavior."""
        for delivery_purpose in ("customer", "analyst"):
            with self.subTest(delivery_purpose=delivery_purpose), ExitStack() as stack:
                stack.enter_context(patch.object(email_reports, "configure_logging"))
                stack.enter_context(patch.object(
                    email_reports, "recover_stale_report_operations_in_db"
                ))
                send_report = stack.enter_context(patch.object(
                    email_reports, "send_report_run_email"
                ))
                self.assertEqual(email_reports.main([
                    "--report-run-id", "9",
                    "--source-email", "sender@example.gov",
                    "--delivery-purpose", delivery_purpose,
                ]), 0)
                self.assertTrue(send_report.call_args.kwargs["allow_held"])
                self.assertEqual(
                    send_report.call_args.kwargs["delivery_purpose"], delivery_purpose
                )


class StandaloneBoundaryTests(unittest.TestCase):
    def test_newlines_rejected(self):
        with self.assertRaises(ValueError):
            standalone_targets.normalized_recipient(
                "a@example.gov\r\nBcc: b@example.gov"
            )

    def test_saved_recipient_revalidated_and_override_forbidden(self):
        row = SimpleNamespace(
            delivery_purpose="standalone", distro_email="saved@example.gov"
        )
        with patch(
            "was_mailer.message.approved_analyst_recipients",
            return_value=["saved@example.gov"],
        ) as validate:
            self.assertEqual(recipient_addresses(row), ["saved@example.gov"])
            validate.assert_called_once_with("saved@example.gov")
        with self.assertRaises(ValueError):
            recipient_addresses(row, "different@example.gov")

    def test_ambiguous_qualys_tag_rejected(self):
        with self.assertRaises(LookupError):
            parse_tag_details(
                "<ServiceResponse><count>2</count><data><Tag><id>1</id></Tag><Tag><id>2</id></Tag></data></ServiceResponse>",
                "TEST",
            )
