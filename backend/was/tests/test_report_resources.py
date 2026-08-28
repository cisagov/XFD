"""Tests for packaged WAS report templates and assets."""

# Standard Python Libraries
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

# First-Party Libraries
from was_reports.resources import (
    REQUIRED_RESOURCE_PATHS,
    missing_report_resources,
    report_resource_root,
    require_report_resources,
)


class ReportResourceTests(unittest.TestCase):
    """Validate the self-contained WAS report resource package."""

    def test_packaged_report_resources_are_complete(self) -> None:
        """Include every required report resource in the source package."""
        resource_root = require_report_resources()

        self.assertEqual(resource_root, report_resource_root())
        self.assertEqual(missing_report_resources(resource_root), ())
        self.assertEqual(len(REQUIRED_RESOURCE_PATHS), 29)

    def test_legacy_creator_is_not_a_packaged_resource(self) -> None:
        """Keep the legacy report creator outside the future resource root."""
        self.assertFalse(
            (report_resource_root() / "WAS_report_creator.py").exists()
        )

    def test_missing_resources_raise_clear_error(self) -> None:
        """Report every missing resource before report generation starts."""
        with TemporaryDirectory() as directory:
            resource_root = Path(directory)

            with self.assertRaisesRegex(
                FileNotFoundError,
                "Missing required WAS report resources",
            ):
                require_report_resources(resource_root)


if __name__ == "__main__":
    unittest.main()
