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
        """Reject existing passwords that contain banned characters."""
        with self.assertRaises(ValueError):
            passwords.validate_report_password("Bad,Password123!")

    def test_validate_report_password_rejects_empty_password(self) -> None:
        """Reject empty passwords."""
        with self.assertRaises(ValueError):
            passwords.validate_report_password("")

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
