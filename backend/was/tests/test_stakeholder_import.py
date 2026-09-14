"""Tests for WAS stakeholder CSV import normalization."""

# Standard Python Libraries
import unittest

# First-Party Libraries
from was_reports.commands.stakeholder_import import normalize_value


class StakeholderImportTests(unittest.TestCase):
    """Validate imported stakeholder field normalization."""

    def test_state_requires_exact_uppercase_valid_code(self) -> None:
        """Accept valid state codes and reject lowercase or unknown values."""
        self.assertEqual(normalize_value("State", "WY", "\\N"), "WY")
        for invalid_state in ("wy", "Wz"):
            with self.subTest(state=invalid_state), self.assertRaises(ValueError):
                normalize_value("State", invalid_state, "\\N")

    def test_blank_state_remains_null(self) -> None:
        """Allow stakeholders without an applicable state to use SQL NULL."""
        self.assertEqual(normalize_value("State", "", "\\N"), "\\N")


if __name__ == "__main__":
    unittest.main()
