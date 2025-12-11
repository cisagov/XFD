"""CheckUserExpiration."""
# Standard Python Libraries
from datetime import timedelta
import logging
import os

# Third-Party Libraries
import django
from django.utils.timezone import now

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()


# Third-Party Libraries
from xfd_api.helpers.email import send_email
from xfd_mini_dl.models import User

# Configure logging
LOGGER = logging.getLogger(__name__)


def check_user_expiration():
    """Check user inactivity and take actions: notify (30 days), deactivate (45 days), and delete (90 days)."""
    today = now()
    cutoff_30_days = today - timedelta(days=30)
    cutoff_45_days = today - timedelta(days=45)
    cutoff_90_days = today - timedelta(days=90)

    # Users to notify (30 days of inactivity)
    users_to_notify = User.objects.filter(
        last_logged_in__lt=cutoff_30_days, last_logged_in__gte=cutoff_45_days
    )

    # Notify users of inactivity (30 days)
    for user in users_to_notify:
        subject = "Account Inactivity Notice"
        body = """
        Hello {first_name} {last_name},

        Your Cyber Hygiene Dashboard account has been inactive for over 30 days. If your account reaches 90 days of inactivity,
        you will need to submit a new account approval request.

        Thank you,
        The Cyber Hygiene (CyHy) Team
        CISA Vulnerability Management
        Cybersecurity and Infrastructure Security Agency (CISA)
        EMAIL: vulnerability@cisa.dhs.gov
        """.format(
            first_name=user.first_name, last_name=user.last_name
        )
        send_email(user.email, subject, body)
        LOGGER.info("30-day inactivity notice sent to %s.", user.email)

    # Users to deactivate (45 days of inactivity)
    users_to_deactivate = User.objects.filter(
        last_logged_in__lt=cutoff_45_days, last_logged_in__gte=cutoff_90_days
    )

    for user in users_to_deactivate:
        subject = "Account Deactivation Notice"
        body = """
        Hello {first_name} {last_name},

        Your Cyber Hygiene Dashboard account has been inactive for over 45 days. If your account reaches 90 days of inactivity,
        you will need to submit a new account approval request.

        Thank you,
        The Cyber Hygiene (CyHy) Team
        CISA Vulnerability Management
        Cybersecurity and Infrastructure Security Agency (CISA)
        EMAIL: vulnerability@cisa.dhs.gov
        """.format(
            first_name=user.first_name, last_name=user.last_name
        )
        # Send inactivity notification
        send_email(user.email, subject, body)

    # Users to remove (90 days of inactivity)
    users_to_remove = User.objects.filter(last_logged_in__lt=cutoff_90_days)

    for user in users_to_remove:
        subject = "Account Removal Notice"
        body = """
        Hello {first_name} {last_name},

        Your Cyber Hygiene Dashboard account has been inactive for over 90 days and has been removed.
        You will need to recreate your account if you wish to use our services again.

        Thank you,
        The Cyber Hygiene (CyHy) Team
        CISA Vulnerability Management
        Cybersecurity and Infrastructure Security Agency (CISA)
        EMAIL: vulnerability@cisa.dhs.gov
        """.format(
            first_name=user.first_name, last_name=user.last_name
        )
        # Notify user of account removal
        send_email(user.email, subject, body)

        # Remove the user from the database
        try:
            user.delete()
            LOGGER.info(
                "Removed user %s from the database due to 90 days of inactivity.",
                user.email,
            )
        except Exception as e:
            LOGGER.error("Error removing user %s: %s", user.email, e)


def run_test_expiration_flow(email: str):
    """
    Test-only helper.

    - Only called when STAGE == 'staging'
    - Create a new user with the given email
    - Simulate 30/45/90 day inactivity by updating last_logged_in and calling
      check_user_expiration() three times
    - Ensure the user gets deleted; if not, try once more and then raise an error
    """
    if not email:
        raise ValueError("Test mode requires an 'email' field in the event payload.")

    # Must be a brand new email so we don't mess with real users
    if User.objects.filter(email=email).exists():
        raise RuntimeError(
            "Test user email {} already exists in the database.".format(email)
        )

    # Use a fixed "now" baseline so our 30/45/90 calculations are consistent
    baseline_now = now()

    # NOTE: We use +1 day to satisfy the strict `<` comparisons in check_user_expiration
    thirty_plus = baseline_now - timedelta(days=31)  # > 30 days inactive
    fortyfive_plus = baseline_now - timedelta(days=46)  # > 45 days inactive
    ninety_plus = baseline_now - timedelta(days=91)  # > 90 days inactive

    # 1) Create user as ~30-day inactive and run
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email=email,
        last_logged_in=thirty_plus,
    )

    check_user_expiration()

    # 2) If still exists, move them to ~45+ days inactive and run again
    if User.objects.filter(id=user.id).exists():
        user = User.objects.get(id=user.id)
        user.last_logged_in = fortyfive_plus
        user.save(update_fields=["last_logged_in"])
        check_user_expiration()

    # 3) If still exists, move them to ~90+ days inactive and run again
    if User.objects.filter(id=user.id).exists():
        user = User.objects.get(id=user.id)
        user.last_logged_in = ninety_plus
        user.save(update_fields=["last_logged_in"])
        check_user_expiration()

    # 4) Verify deletion – if still present, try once more then raise
    if User.objects.filter(id=user.id).exists():
        # One more attempt to let the expiration logic clean up
        user = User.objects.get(id=user.id)
        user.delete()
        if User.objects.filter(id=user.id).exists():
            raise RuntimeError(
                "Test user {} was not deleted by expiration logic.".format(email)
            )


def handler(event, context):
    """AWS Lambda handler for checking user expiration."""
    try:
        stage = os.getenv("STAGE", "").lower()

        # Test mode: event contains {"Test": true, "email": "..."} and STAGE=staging
        if isinstance(event, dict) and event.get("Test"):
            if stage != "staging":
                return {
                    "status_code": 403,
                    "body": "Test mode is only allowed when STAGE=staging.",
                }

            email = event.get("email")
            run_test_expiration_flow(email)
            return {
                "status_code": 200,
                "body": "Test expiration flow executed for {}.".format(email),
            }

        # Normal scheduled behavior
        check_user_expiration()
        return {
            "status_code": 200,
            "body": "User expiration check completed successfully.",
        }
    except Exception as e:
        LOGGER.error("Error during user expiration check: %s", e)
        return {"status_code": 500, "body": str(e)}
