"""Tests for WAS stakeholder CSV import normalization."""

# Standard Python Libraries
import unittest

# First-Party Libraries
from was_reports.commands.stakeholder_import import (
    normalize_imported_report_password,
    normalize_value,
)


class StakeholderImportTests(unittest.TestCase):
    """Validate imported stakeholder field normalization."""

    def test_state_requires_exact_uppercase_valid_code(self) -> None:
        """Accept valid state codes and reject lowercase or unknown values."""
        self.assertEqual(normalize_value("State", "WY", "\\N"), "WY")
        for invalid_state in ("wy", "Wz"):
            with self.subTest(state=invalid_state), self.assertRaises(ValueError):
                normalize_value("State", invalid_state, "\\N")

    def test_blank_state_is_rejected(self) -> None:
        """Require imported stakeholders to include a state."""
        with self.assertRaisesRegex(ValueError, "State must not be null"):
            normalize_value("State", "", "\\N")

    def test_import_date_accepts_yyyy_mm_dd(self) -> None:
        """Normalize imported date-only input to an epoch value."""
        self.assertEqual(
            normalize_value("Onboarding Date", "2026-09-16", "\\N"),
            "1789516800",
        )

    def test_import_email_rejects_newline(self) -> None:
        """Reject imported email fields that contain header-injection data."""
        with self.assertRaisesRegex(ValueError, "line breaks"):
            normalize_value(
                "Distro Email",
                "customer@example.gov\nmalicious@example.gov",
                "\\N",
            )

    def test_import_removes_legacy_password_wrapper(self) -> None:
        """Remove DynamoDB string wrappers from generated passwords."""
        password = '"Abcdefghijklmnopqrst123!"'

        self.assertEqual(
            normalize_imported_report_password(password),
            "Abcdefghijklmnopqrst123!",
        )

    def test_import_decodes_multiple_doubled_password_quotes(self) -> None:
        """Decode every CSV-doubled quote inside a wrapped password."""
        password = '"Abcd""efghijkl""mnopqr123!"'

        self.assertEqual(
            normalize_value("Report Password", password, "\\N"),
            'Abcd"efghijkl"mnopqr123!',
        )

    def test_import_decodes_unwrapped_doubled_password_quotes(self) -> None:
        """Repair previously unwrapped passwords that retain doubled quotes."""
        password = 'Abcd""efghijkl""mnopqr123!'

        self.assertEqual(
            normalize_imported_report_password(password),
            'Abcd"efghijkl"mnopqr123!',
        )

    def test_import_preserves_short_customer_password_quotes(self) -> None:
        """Do not reinterpret shorter customer-provided passwords."""
        password = 'Valid""Password1!'

        self.assertEqual(normalize_imported_report_password(password), password)


if __name__ == "__main__":
    unittest.main()
