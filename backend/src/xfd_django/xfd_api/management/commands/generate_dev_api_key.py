"""
Generate a new API key for an existing user and (optionally) write it to xfd_api/tasks/.env.

Usage:
    python manage.py generate_dev_api_key --email <your_user_name>@<your_domain_name>
    python manage.py generate_dev_api_key                     # uses LOCAL_MDL_USERNAME
    python manage.py generate_dev_api_key --no-write-env
"""

# Standard Python Libraries
import os
from typing import Optional

# Third-Party Libraries
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Use your existing helpers exactly as named.
from xfd_api.tasks.helpers.syncdb_helpers.create_sample_data import (  # type: ignore
    create_api_key_for_user,
    write_api_key_to_env_file,
)

# Import your concrete model (NOT Django auth user).
from xfd_mini_dl.models import ApiKey, User  # adjust import path if needed


def resolve_email(variable_name: str, explicit_email: Optional[str]) -> str:
    """
    Resolve the email address to target for API key generation.

    Priority:
        1) explicit_email if provided
        2) environment variable named variable_name

    Raises:
        CommandError: if no email is available or clearly malformed.
    """
    resolved = (explicit_email or os.environ.get(variable_name) or "").strip()

    if not resolved:
        raise CommandError(
            f"Provide --email or set the {variable_name} environment variable."
        )

    # Simple sanity checks without regex (your preference).
    if "@" not in resolved:
        raise CommandError(f"Email '{resolved}' is invalid: missing '@'.")
    local_part, domain_part = resolved.split("@", maxsplit=1)
    if not local_part or not domain_part or "." not in domain_part:
        raise CommandError(f"Email '{resolved}' is invalid: malformed domain.")

    return resolved


def get_existing_user(email: str) -> User:
    """
    Fetch an existing user by email.

    Raises:
        CommandError: if the user does not exist.
    """
    user = User.objects.filter(email=email).first()
    if user is None:
        raise CommandError(
            f"User with email '{email}' not found. This command does not create users."
        )
    return user


class Command(BaseCommand):
    """Generate and store a new API key for an existing user."""

    help = (
        "Create a new API key for an existing user (by --email or LOCAL_MDL_USERNAME) "
        "and write CF_API_KEY to xfd_api/tasks/.env unless --no-write-env is set."
    )

    def add_arguments(self, parser) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--env-var",
            type=str,
            default="LOCAL_MDL_USERNAME",
            help="Env var to read when --email is not provided (default: LOCAL_MDL_USERNAME).",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Target user's email address (takes precedence over env var).",
        )
        parser.add_argument(
            "--no-write-env",
            action="store_true",
            help="Do not write CF_API_KEY to xfd_api/tasks/.env.",
        )

    def handle(self, *args, **options) -> None:
        """
        Generate a new API key for an existing user unless one already exists.

        Behavior:
          - Resolves the target email (CLI --email or env var).
          - Verifies the user exists.
          - If an ApiKey already exists for the user, raises CommandError (no new key created).
          - Otherwise creates a new key and writes CF_API_KEY to xfd_api/tasks/.env
            unless --no-write-env is provided.
        """
        environment_variable_name: str = options["env_var"]
        explicit_email: Optional[str] = options.get("email")
        skip_env_write: bool = bool(options["no_write_env"])

        email = resolve_email(environment_variable_name, explicit_email)

        with transaction.atomic():
            user = get_existing_user(email)

            # Prevent duplicates: if a key already exists, fail fast with context.
            existing_key = (
                ApiKey.objects.filter(user=user).order_by("-created_at").first()
            )
            if existing_key is not None:
                raise CommandError(
                    f"User '{email}' already has an API key (last four: "
                    f"{existing_key.last_four}). No new key created."
                )

            raw_key = create_api_key_for_user(user)  # must return the raw key

        if not raw_key:
            raise CommandError(
                "create_api_key_for_user(user) did not return a key. "
                "Ensure your helper returns the raw key and does not only log it."
            )

        self.stdout.write(self.style.SUCCESS(f"API key created for {email}."))

        if skip_env_write:
            self.stdout.write("Skipping .env write (--no-write-env).")
            return

        write_api_key_to_env_file(raw_key)
        self.stdout.write(
            self.style.SUCCESS("CF_API_KEY written to xfd_api/tasks/.env.")
        )
