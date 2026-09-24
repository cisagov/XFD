"""Tests for WAS report password helpers."""

# Standard Python Libraries
import os
import string
import unittest
from unittest.mock import patch

# First-Party Libraries
from was_reports.utils import passwords


class PasswordTests(unittest.TestCase):
    """Validate WAS password generation and policy enforcement."""

    def test_generate_report_password_uses_allowed_characters(self) -> None:
        """Generate passwords without banned command-sensitive characters."""
        password = passwords.generate_report_password(length=24)

        self.assertEqual(len(password), 24)
        self.assertFalse(set(password) & passwords.BANNED_PASSWORD_CHARACTERS)

    def test_generate_report_password_requires_minimum_length(self) -> None:
        """Reject weak generated password lengths."""
        with self.assertRaises(ValueError):
            passwords.generate_report_password(length=8)

    def test_validate_report_password_rejects_banned_characters(self) -> None:
        """Reject commas and hyphens in newly entered passwords."""
        for report_password in (
            "Bad,Password123!", "Bad-Password123!", " BadPassword123! ",
        ):
            with self.subTest(report_password=report_password):
                with self.assertRaises(ValueError):
                    passwords.validate_report_password(report_password)

    def test_existing_password_accepts_legacy_punctuation(self) -> None:
        """Accept commas and hyphens already stored for PDF encryption."""
        passwords.validate_existing_report_password("Legacy,Password123!")
        passwords.validate_existing_report_password("Legacy-Password123!")

    def test_existing_password_accepts_literal_spaces(self) -> None:
        """Allow intentional spaces at either edge and within existing passwords."""
        for report_password in (
            " LegacyPassword123!", "LegacyPassword123! ", "Legacy Password123!",
        ):
            with self.subTest(report_password=report_password):
                passwords.validate_existing_report_password(report_password)

    def test_existing_password_rejects_empty_controls_and_non_ascii(self) -> None:
        """Do not broaden compatibility to control characters or other encodings."""
        for report_password in (
            "", "Legacy\tPassword123!", "Legacy\nPassword123!",
            "Legacy\rPassword123!", "Legacy\x00Password123!",
            "Legacy\x7fPassword123!", "Legacy\u00a0Password123!",
        ):
            with self.subTest(report_password=report_password):
                with self.assertRaises(ValueError):
                    passwords.validate_existing_report_password(report_password)

    def test_validation_error_does_not_disclose_password_character(self) -> None:
        """Keep rejected password characters out of errors and downstream logs."""
        with self.assertRaisesRegex(ValueError, "unsupported character") as error:
            passwords.validate_existing_report_password("Legacy\u00e9Password123!")
        self.assertNotIn("\u00e9", str(error.exception))

    def test_validate_report_password_accepts_apostrophe(self) -> None:
        """Accept an apostrophe in an existing stakeholder report password."""
        passwords.validate_report_password("Valid'Password123!")

    def test_validate_report_password_rejects_empty_password(self) -> None:
        """Reject empty passwords."""
        with self.assertRaises(ValueError):
            passwords.validate_report_password("")

    def test_customer_password_requires_length_and_character_classes(self) -> None:
        """Reject customer passwords that do not meet the complete policy."""
        invalid_passwords = (
            "Short1!",
            "UPPERCASEPASSWORD1!",
            "lowercasepassword1!",
            "PasswordWithoutNumber!",
            "PasswordWithoutSpecial1",
            " CustomerPassword123! ",
            "Customer,Password123!",
            "Customer-Password123!",
        )
        for report_password in invalid_passwords:
            with self.subTest(report_password=report_password):
                with self.assertRaises(ValueError):
                    passwords.validate_customer_provided_report_password(
                        report_password
                    )

    def test_customer_password_accepts_complete_policy(self) -> None:
        """Accept a customer password that meets every WAS requirement."""
        passwords.validate_customer_provided_report_password(
            "CustomerPassword123!"
        )

    def test_password_character_set_contains_required_classes(self) -> None:
        """Keep enough character classes for strong generated passwords."""
        self.assertTrue(
            set(passwords.PASSWORD_CHARACTER_SET) & set(string.ascii_lowercase)
        )
        self.assertTrue(
            set(passwords.PASSWORD_CHARACTER_SET) & set(string.ascii_uppercase)
        )
        self.assertTrue(set(passwords.PASSWORD_CHARACTER_SET) & set(string.digits))
        self.assertTrue(set(passwords.PASSWORD_CHARACTER_SET) & set(string.punctuation))

    @patch.dict(os.environ, {"WAS_PASSWORD_LENGTH": "32"})
    def test_password_length_from_environment(self) -> None:
        """Allow deployments to configure generated password length."""
        self.assertEqual(passwords.password_length_from_environment(), 32)

    @patch.dict(os.environ, {"WAS_PASSWORD_LENGTH": "12"})
    def test_password_length_from_environment_requires_minimum(self) -> None:
        """Reject environment configured weak password lengths."""
        with self.assertRaises(ValueError):
            passwords.password_length_from_environment()


if __name__ == "__main__":
    unittest.main()
