"""Tests for the accounts application."""

# Standard Python Libraries
import uuid

# Third-Party Libraries
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase


class UserModelDefinitionTests(SimpleTestCase):
    """Verify the custom user model's identity and WAS-specific fields."""

    def test_user_uses_uuid_primary_key_and_standard_name_fields(self) -> None:
        """Use UUID identity while retaining Django's standard name behavior."""
        user_model = get_user_model()
        user = user_model(
            username="mina.salehi",
            first_name="Mina",
            last_name="Salehi",
            email="mina.salehi@example.gov",
        )

        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.get_full_name(), "Mina Salehi")
        self.assertTrue(user.is_active)

    def test_user_email_is_unique_and_email_delivery_is_enabled(self) -> None:
        """Require one login email and enable WAS email delivery by default."""
        user_model = get_user_model()
        user = user_model(
            username="tenesa.ellis",
            email="tenesa.ellis@example.gov",
        )
        email_field = user_model._meta.get_field("email")

        self.assertTrue(email_field.unique)
        self.assertTrue(user.email_enabled)

    def test_user_tracks_django_and_update_timestamps(self) -> None:
        """Retain Django's join date and add an automatically updated timestamp."""
        user_model = get_user_model()
        date_joined_field = user_model._meta.get_field("date_joined")
        updated_at_field = user_model._meta.get_field("updated_at")

        self.assertTrue(date_joined_field.has_default())
        self.assertTrue(updated_at_field.auto_now)
