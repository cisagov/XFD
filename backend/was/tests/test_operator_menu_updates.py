"""Operator menu organization, export safety, and guarded tracker corrections."""

import ast
import csv
from datetime import date
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, MagicMock, patch

from was_reports.commands.menu_cli import WasOperatorMenu
from was_reports.commands import tracker_cli
from was_reports.data import daily_report_tracker, tracker_corrections
from was_reports.storage import tracker_exports
from was_reports.utils.stakeholder_options import STAKEHOLDER_OPTIONS


class MenuUpdatesTests(unittest.TestCase):
    def menu(self, answers):
        menu = WasOperatorMenu(
            input_function=Mock(side_effect=answers),
            output_function=Mock(),
            secret_input_function=Mock(),
        )
        menu.pause = Mock()
        return menu

    def test_navigation_is_zero_and_first(self):
        for method, navigation in [
            ("run", "Quit"),
            ("report_menu", "Back to main menu"),
            ("tracker_menu", "Back to main menu"),
            ("stakeholder_menu", "Back to main menu"),
        ]:
            with self.subTest(menu=method):
                menu = self.menu(["0"])
                getattr(menu, method)()
                options = [
                    c.args[0]
                    for c in menu.output.call_args_list
                    if c.args[0][:1].isdigit()
                ]
                self.assertEqual(options[0], "0) " + navigation)

    @patch("was_reports.commands.menu_cli.batch_runner.main", return_value=0)
    def test_automated_reports_are_not_limited_to_a_tag(self, run):
        menu = self.menu(["", "y"])
        menu.run_automated_reports()
        args = run.call_args.args[0]
        self.assertNotIn("--tag", args)
        self.assertNotIn("--limit", args)
        self.assertIn("--skip-tracker-refresh", args)
        self.assertEqual(args[args.index("--days-back") + 1], "7")

    @patch("was_reports.commands.menu_cli.tracker_cli.main", return_value=0)
    def test_customer_history_includes_children_without_date_or_row_limit(self, run):
        menu = self.menu(["PARENT", "y"])
        menu.view_customer_tracker()
        run.assert_called_once_with(
            [
                "show",
                "--tag",
                "PARENT",
                "--all-dates",
                "--limit",
                "all",
                "--include-children",
            ]
        )

    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli.get_stakeholder_record_by_tag",
        side_effect=KeyError("not found"),
    )
    def test_missing_stakeholder_stops_before_more_inputs(self, lookup):
        for method in (
            "update_stakeholder_contacts",
            "rotate_stakeholder_password",
            "retrieve_stakeholder_password",
            "set_customer_provided_password",
        ):
            with self.subTest(method=method):
                menu = self.menu(["MISSING"])
                getattr(menu, method)()
                self.assertEqual(menu.input.call_count, 1)
                menu.secret_input.assert_not_called()

    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli.get_stakeholder_record_by_tag",
        return_value={"tag": "EXISTS"},
    )
    def test_add_rejects_existing_tag_before_other_inputs(self, lookup):
        menu = self.menu(["EXISTS"])
        menu.add_stakeholder()
        self.assertEqual(menu.input.call_count, 1)

    @patch("was_reports.commands.menu_cli.stakeholders_cli.main")
    @patch(
        "was_reports.commands.menu_cli.stakeholders_cli.get_stakeholder_record_by_tag"
    )
    def test_contact_prompts_show_current_values_and_enter_keeps_them(
        self, lookup, run
    ):
        lookup.return_value = {
            "tag": "TAG",
            "was_report_poc": "First Last",
            "tech_poc_email": "poc@example.gov",
            "distro_email": "team@example.gov",
        }
        menu = self.menu(["TAG", "", "", ""])
        menu.update_stakeholder_contacts()
        run.assert_not_called()
        prompts = [call.args[0] for call in menu.input.call_args_list]
        self.assertIn("First Last", prompts[1])
        self.assertIn("poc@example.gov", prompts[2])
        self.assertIn("team@example.gov", prompts[3])

    def test_menu_enum_suggestions_match_model(self):
        tree = ast.parse(
            (Path(__file__).parents[1] / "schema/stakeholders.py").read_text()
        )
        names = {
            "CITypeChoices": "ci_type",
            "TestingSectorChoices": "testing_sector",
            "SubtypeChoices": "subtype",
            "FrequencyChoices": "frequency",
        }
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name in names:
                values = []
                for assignment in node.body:
                    if isinstance(assignment, ast.Assign):
                        value = ast.literal_eval(assignment.value)
                        if isinstance(value, tuple):
                            value = value[0]
                        if value:
                            values.append(value)
                self.assertEqual(tuple(values), STAKEHOLDER_OPTIONS[names[node.name]])


class TrackerExportTests(unittest.TestCase):
    @patch.object(tracker_cli, "require_env", return_value="reports@example.gov")
    @patch.object(tracker_cli, "create_ses_client")
    @patch.object(tracker_cli, "send_message", return_value="message-id")
    @patch.object(
        tracker_cli, "approved_analyst_recipients", return_value=["analyst@example.gov"]
    )
    @patch.object(tracker_cli, "list_tracker_rows_for_export_from_db")
    def test_email_export_excludes_passwords_and_escapes_formulas(
        self, rows, approve, send, ses, env
    ):
        rows.return_value = [
            daily_report_tracker.DailyReportTrackerRow(
                tag="=formula", legacy_password="PRIVATE_SECRET"
            )
        ]
        tracker_cli.main(["export-csv", "--email-assignee", "analyst@example.gov"])
        message = send.call_args.args[1]
        csv_text = list(message.iter_attachments())[0].get_payload(decode=True).decode()
        data = list(csv.reader(StringIO(csv_text)))
        self.assertNotIn("Password", data[0])
        self.assertNotIn("PRIVATE_SECRET", csv_text)
        self.assertEqual(data[1][1], "'=formula")
        self.assertEqual(message["To"], "analyst@example.gov")

    @patch.object(
        tracker_cli, "upload_tracker_export", return_value="s3://test/export.csv"
    )
    @patch.object(tracker_cli, "list_tracker_rows_for_export_from_db", return_value=[])
    def test_direct_s3_export(self, rows, upload):
        tracker_cli.main(["export-csv", "--s3"])
        upload.assert_called_once()

    @patch.object(tracker_exports, "reports_bucket_name", return_value="test")
    @patch.object(tracker_exports, "reports_prefix", return_value="was_reports")
    def test_s3_key_and_encryption(self, prefix, bucket):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "export.csv"
            path.touch()
            client = Mock()
            uri = tracker_exports.upload_tracker_export(path, client)
            self.assertIn("/tracker_exports/", uri)
            self.assertEqual(
                client.upload_file.call_args.kwargs["ExtraArgs"][
                    "ServerSideEncryption"
                ],
                "AES256",
            )

    def test_child_query_uses_recursive_parent_relationship_not_tag_prefix(self):
        conn = MagicMock()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        daily_report_tracker.list_tracker_table_rows(
            conn, None, limit=None, stakeholder_tag="PARENT_1", include_children=True
        )
        query, args = cursor.execute.call_args.args
        self.assertIn("WITH RECURSIVE", query)
        self.assertIn("UNION", query)
        self.assertNotIn("LIKE", query)
        self.assertNotIn("CURRENT_DATE", query)
        self.assertNotIn(" LIMIT ", query)
        self.assertEqual(args, ("PARENT_1", "PARENT_1"))


class TrackerCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value.__enter__.return_value
        self.cursor.fetchone.side_effect = [(1,), None]
        self.record = {
            "id": 1,
            "report_sent_date": None,
            "assignee_email_status": "pending",
        }
        for name, options in [
            ("connect", {"return_value": self.conn}),
            ("close", {}),
            ("get_tracker_record_by_id", {"return_value": self.record}),
        ]:
            patcher = patch.object(tracker_corrections, name, **options)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_unclaimed_row_can_be_corrected(self):
        tracker_corrections.correct_tracker_row(
            1, {"report_scan_notes": None}, expected=self.record.copy()
        )
        self.conn.commit.assert_called_once()

    def test_sent_row_is_protected(self):
        self.record["report_sent_date"] = date.today()
        with self.assertRaisesRegex(ValueError, "Sent rows"):
            tracker_corrections.correct_tracker_row(
                1, {"report_scan_notes": None}, expected=self.record.copy()
            )
        self.conn.commit.assert_not_called()

    def test_existing_run_is_protected(self):
        self.cursor.fetchone.side_effect = [(1,), (42,)]
        with self.assertRaisesRegex(ValueError, "report run already exists"):
            tracker_corrections.correct_tracker_row(
                1, {"report_scan_notes": None}, expected=self.record.copy()
            )
        self.conn.rollback.assert_called_once()

    def test_changed_row_is_protected(self):
        with self.assertRaisesRegex(ValueError, "changed since inspection"):
            tracker_corrections.correct_tracker_row(
                1, {"report_scan_notes": None}, expected={}
            )

    def test_identity_and_delivery_columns_are_protected(self):
        for field in (
            "tag",
            "schedule_id",
            "scan_start_date",
            "scan_execution_key",
            "report_sent_date",
            "legacy_password",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                tracker_corrections.correct_tracker_row(
                    1, {field: None}, expected=self.record.copy()
                )
        tracker_corrections.connect.assert_not_called()
