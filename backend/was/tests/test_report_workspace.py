"""Tests for isolated WAS report workspaces and output locks."""

# Standard Python Libraries
import tempfile
import unittest
from datetime import date
from pathlib import Path

# First-Party Libraries
from was_reports import report_workspace


class ReportWorkspaceTests(unittest.TestCase):
    """Validate report filesystem isolation and concurrency controls."""

    def test_workspace_copies_legacy_assets_and_cleans_up(self) -> None:
        """Provide required assets privately and remove them after use."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_root = root / "legacy"
            workspace_root = root / "workspaces"
            (legacy_root / "assets").mkdir(parents=True)
            (legacy_root / "NEW_BIG.mustache").write_text("template")
            (legacy_root / "assets" / "background.pdf").write_bytes(b"pdf")

            with report_workspace.isolated_report_workspace(
                legacy_root,
                workspace_root,
                "CUSTOMER",
            ) as workspace_path:
                self.assertTrue((workspace_path / "NEW_BIG.mustache").is_file())
                self.assertTrue(
                    (workspace_path / "assets" / "background.pdf").is_file()
                )
                captured_workspace = workspace_path

            self.assertFalse(captured_workspace.exists())

    def test_workspace_cleans_up_after_failure(self) -> None:
        """Remove sensitive temporary artifacts when generation fails."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_root = root / "legacy"
            legacy_root.mkdir()

            with self.assertRaises(RuntimeError):
                with report_workspace.isolated_report_workspace(
                    legacy_root,
                    root / "workspaces",
                    "CUSTOMER",
                ) as workspace_path:
                    (workspace_path / "sensitive.csv").write_text("sensitive")
                    captured_workspace = workspace_path
                    raise RuntimeError("generation failed")

            self.assertFalse(captured_workspace.exists())

    def test_output_lock_rejects_duplicate_report(self) -> None:
        """Prevent simultaneous writes to the same dated report output."""
        with tempfile.TemporaryDirectory() as directory:
            output_directory = Path(directory)
            with report_workspace.report_output_lock(
                output_directory,
                "CUSTOMER",
                date(2026, 8, 27),
            ):
                with self.assertRaises(RuntimeError):
                    with report_workspace.report_output_lock(
                        output_directory,
                        "CUSTOMER",
                        date(2026, 8, 27),
                    ):
                        pass


if __name__ == "__main__":
    unittest.main()
