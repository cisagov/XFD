"""Helper for importing test users from a JSON file."""

# Standard Python Libraries
from datetime import datetime
import json
import logging

# Third-Party Libraries
from django.db import IntegrityError, transaction

# Local Libraries
from xfd_mini_dl.models import User

LOGGER = logging.getLogger(__name__)


@transaction.atomic
def import_test_users_from_json(json_path: str):
    """Import test users from a JSON file exported for local development."""
    LOGGER.info("📥 Importing test users from %s", json_path)

    # Step 1. Read file
    try:
        with open(json_path, encoding="utf-8") as f:
            raw_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        LOGGER.error("❌ Failed to read or parse test users file: %s", e)
        return

    # Step 2. Validate structure
    if not isinstance(raw_data, dict) or "user" not in raw_data:
        LOGGER.error("❌ Expected top-level key 'user' in JSON file.")
        return

    users = raw_data["user"]
    if not isinstance(users, list):
        LOGGER.error("❌ Expected 'user' to be a list; got %s", type(users).__name__)
        return

    LOGGER.info("🧩 Found %d users in file.", len(users))

    # Step 3. Iterate and create users
    for entry in users:
        try:
            email = entry.get("email")
            if not email:
                LOGGER.warning("⚠️ Skipping entry with no email: %s", entry)
                continue

            # Map and sanitize fields
            defaults = {
                "first_name": entry.get("first_name", ""),
                "last_name": entry.get("last_name", ""),
                "full_name": entry.get("full_name", ""),
                "invite_pending": entry.get("invite_pending", False),
                "first_login": entry.get("first_login", False),
                "can_select_own_state": entry.get("can_select_own_state", False),
                "date_approved": parse_timestamp(entry.get("date_approved")),
                "date_accepted_terms": parse_timestamp(
                    entry.get("date_accepted_terms")
                ),
                "accepted_terms_version": entry.get("accepted_terms_version"),
                "last_logged_in": parse_timestamp(entry.get("last_logged_in")),
                "region_id": entry.get("region_id"),
                "state": entry.get("state"),
                "okta_id": entry.get("okta_id"),
                "cognito_id": entry.get("cognito_id"),
                "cognito_username": entry.get("cognito_username"),
                "login_gov_id": entry.get("login_gov_id"),
                "user_type": normalize_user_type(entry.get("user_type")),
            }

            user, created = User.objects.update_or_create(
                id=entry.get("id"), defaults=defaults, email=email
            )

            LOGGER.info(
                "✅ %s user %s (%s)",
                "Created" if created else "Updated",
                email,
                defaults["user_type"],
            )

        except IntegrityError as e:
            LOGGER.error("❌ Integrity error for user %s: %s", entry.get("email"), e)
        except Exception as e:
            LOGGER.error(
                "❌ Unexpected error creating user %s: %s", entry.get("email"), e
            )


def parse_timestamp(value):
    """Safely parse ISO timestamps."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def normalize_user_type(raw_type):
    """Normalize user_type field to expected DB enum/constant."""
    if not raw_type:
        return "standard"
    return raw_type.lower()
