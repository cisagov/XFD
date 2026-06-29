"""Tests for checkUserExpiration Lambda task."""
# Standard Python Libraries
from datetime import timedelta
import json

# Third-Party Libraries
from django.utils import timezone
import pytest
from xfd_api.tasks import checkUserExpiration
from xfd_mini_dl.models import Log, Organization, Role, User, UserType

# import logging
# import os

# import django
# from django.db.models.query import Q
# from django.utils.timezone import now


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_check_user_expiration_sends_30_once_and_deletes_at_45(monkeypatch):
    """Test check user expiration sends 30 days once and deletes at 45."""
    frozen_now = timezone.now()
    monkeypatch.setattr(checkUserExpiration, "now", lambda: frozen_now)

    emails_sent = []

    def fake_send_email(to_addr, subject, body):
        emails_sent.append({"to": to_addr, "subject": subject, "body": body})

    monkeypatch.setattr(checkUserExpiration, "send_email", fake_send_email)

    # 20 days inactive -> no email, not deleted
    user_20 = User.objects.create(
        first_name="Twenty",
        last_name="Days",
        email="20@example.com",
        last_logged_in=frozen_now - timedelta(days=20),
    )

    # 35 days inactive -> should get 30-day notice once, not deleted
    user_35 = User.objects.create(
        first_name="ThirtyFive",
        last_name="Days",
        email="35@example.com",
        last_logged_in=frozen_now - timedelta(days=35),
        last_notified_30=None,
    )

    # 60 days inactive -> should get deletion notice and be deleted
    user_60 = User.objects.create(
        first_name="Sixty",
        last_name="Days",
        email="60@example.com",
        last_logged_in=frozen_now - timedelta(days=60),
    )

    checkUserExpiration.check_user_expiration()

    assert User.objects.filter(id=user_20.id).exists()
    assert User.objects.filter(id=user_35.id).exists()
    assert not User.objects.filter(id=user_60.id).exists()

    # Should have sent:
    # - one 30-day notice to user_35
    # - one 45-day removal notice to user_60
    assert len(emails_sent) == 2

    by_to = {}
    for e in emails_sent:
        by_to.setdefault(e["to"], []).append(e)

    assert "20@example.com" not in by_to

    assert "35@example.com" in by_to
    assert len(by_to["35@example.com"]) == 1
    assert by_to["35@example.com"][0]["subject"] == "Account Inactivity Notice"
    assert "inactive for over 30 days" in by_to["35@example.com"][0]["body"]

    assert "60@example.com" in by_to
    assert len(by_to["60@example.com"]) == 1
    assert by_to["60@example.com"][0]["subject"] == "Account Removal Notice"
    assert "inactive for over 45 days" in by_to["60@example.com"][0]["body"]

    # last_notified_30 should have been set for user_35
    user_35.refresh_from_db()
    assert user_35.last_notified_30 is not None


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_check_user_expiration_does_not_repeat_30_day_email(monkeypatch):
    """Test check user expiration does not repeat 30 day email."""
    frozen_now = timezone.now()
    monkeypatch.setattr(checkUserExpiration, "now", lambda: frozen_now)

    emails_sent = []

    def fake_send_email(to_addr, subject, body):
        """Test fake send email."""
        emails_sent.append({"to": to_addr, "subject": subject, "body": body})

    monkeypatch.setattr(checkUserExpiration, "send_email", fake_send_email)

    # In the 30–45 window, but already notified
    user = User.objects.create(
        first_name="Already",
        last_name="Notified",
        email="already@example.com",
        last_logged_in=frozen_now - timedelta(days=35),
        last_notified_30=frozen_now - timedelta(days=1),
    )

    checkUserExpiration.check_user_expiration()

    assert User.objects.filter(id=user.id).exists()
    assert not emails_sent


def test_handler_success(monkeypatch):
    """Test handler success."""
    called = {"count": 0}

    def fake_check():
        called["count"] += 1

    monkeypatch.setattr(checkUserExpiration, "check_user_expiration", fake_check)

    response = checkUserExpiration.handler(event={}, context={})

    assert called["count"] == 1
    assert response["status_code"] == 200
    assert "completed successfully" in response["body"]


def test_handler_failure(monkeypatch):
    """Test handler failure."""

    def fake_check():
        raise RuntimeError("boom")

    monkeypatch.setattr(checkUserExpiration, "check_user_expiration", fake_check)

    response = checkUserExpiration.handler(event={}, context={})

    assert response["status_code"] == 500
    assert "boom" in response["body"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_handler_test_mode_staging_creates_and_deletes_user(monkeypatch):
    """Test handler test mode staging."""
    monkeypatch.setenv("STAGE", "staging")

    fixed_now = timezone.now()
    monkeypatch.setattr(checkUserExpiration, "now", lambda: fixed_now)

    emails = []

    def fake_send_email(to_addr, subject, body):
        emails.append({"to": to_addr, "subject": subject, "body": body})

    monkeypatch.setattr(checkUserExpiration, "send_email", fake_send_email)

    event = {"Test": True, "email": "uat@example.com"}

    response = checkUserExpiration.handler(event=event, context={})

    assert response["status_code"] == 200
    assert "uat@example.com" in response["body"]

    # User should have been created and then deleted at 45
    assert not User.objects.filter(email="uat@example.com").exists()

    # With delete-at-45 logic, test flow should trigger exactly:
    # - 30-day notice
    # - 45-day deletion notice
    assert len(emails) == 2
    subjects = {e["subject"] for e in emails}
    assert "Account Inactivity Notice" in subjects
    assert "Account Removal Notice" in subjects


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_handler_test_mode_existing_email_raises(monkeypatch):
    """Test handler test mode existing email raises."""
    monkeypatch.setenv("STAGE", "staging")

    User.objects.create(
        first_name="Existing",
        last_name="User",
        email="uat@example.com",
        last_logged_in=timezone.now(),
    )

    emails = []

    def fake_send_email(to_addr, subject, body):
        emails.append({"to": to_addr, "subject": subject, "body": body})

    monkeypatch.setattr(checkUserExpiration, "send_email", fake_send_email)

    event = {"Test": True, "email": "uat@example.com"}
    response = checkUserExpiration.handler(event=event, context={})

    assert response["status_code"] == 500
    assert "already exists" in response["body"]
    assert not emails


def test_handler_test_mode_forbidden_when_not_staging(monkeypatch):
    """Test handler test mode forbidden environments."""
    monkeypatch.setenv("STAGE", "production")

    called = {"count": 0}

    def fake_check():
        called["count"] += 1

    monkeypatch.setattr(checkUserExpiration, "check_user_expiration", fake_check)

    emails = []

    def fake_send_email(to_addr, subject, body):
        emails.append({"to": to_addr, "subject": subject, "body": body})

    monkeypatch.setattr(checkUserExpiration, "send_email", fake_send_email)

    event = {"Test": True, "email": "uat@example.com"}
    response = checkUserExpiration.handler(event=event, context={})

    assert response["status_code"] == 403
    assert "only allowed" in response["body"]
    assert called["count"] == 0
    assert not emails


@pytest.mark.django_db(transaction=False, databases=["default", "mini_data_lake"])
def test_check_user_expiration_creates_audit_log_on_success(monkeypatch):
    """Test that a valid JSON audit entry is added to Log upon user deletion."""
    frozen_now = timezone.now()
    monkeypatch.setattr(checkUserExpiration, "now", lambda: frozen_now)

    # Suppress email alerts
    monkeypatch.setattr(checkUserExpiration, "send_email", lambda *args, **kwargs: None)

    # Create a user exceeding the 45-day threshold
    expired_user = User.objects.create(
        first_name="Audit",
        last_name="Success",
        email="audit_success@example.com",
        last_logged_in=frozen_now - timedelta(days=50),
    )

    # Run the core expiration function
    checkUserExpiration.check_user_expiration()

    # Confirm user removal
    assert not User.objects.filter(id=expired_user.id).exists()

    # Validate that the audit Log was generated correctly
    audit_log = Log.objects.filter(
        event_type="REMOVED BY INACTIVITY", result="success"
    ).first()

    assert audit_log is not None
    assert abs(audit_log.created_at - frozen_now) < timedelta(seconds=1)

    # Unpack the JSON payload string and inspect fields
    payload = json.loads(audit_log.payload)
    assert payload["job"] == "check_user_expiration"
    assert payload["action_reason"] == "45 days of inactivity"
    assert payload["user"]["id"] == str(expired_user.id)
    assert payload["user"]["email"] == "audit_success@example.com"
    assert payload["user"]["full_name"] == "Audit Success"
    assert payload["user"]["last_logged_in"] == expired_user.last_logged_in.isoformat()
    assert payload["user"]["user_type"] == UserType.STANDARD
    assert "cognito_id" not in payload["user"]
    assert "organization" not in payload


@pytest.mark.django_db(transaction=False, databases=["default", "mini_data_lake"])
def test_check_user_expiration_audit_log_includes_organization(monkeypatch):
    """Test audit log includes organization from the user's first role."""
    frozen_now = timezone.now()
    monkeypatch.setattr(checkUserExpiration, "now", lambda: frozen_now)
    monkeypatch.setattr(checkUserExpiration, "send_email", lambda *args, **kwargs: None)

    organization = Organization.objects.create(
        name="Inactive Org",
        root_domains=["example.gov"],
        ip_blocks=[],
        is_passive=False,
        created_at=frozen_now,
        updated_at=frozen_now,
    )
    expired_user = User.objects.create(
        first_name="Org",
        last_name="Member",
        email="audit_org@example.com",
        user_type=UserType.STANDARD,
        last_logged_in=frozen_now - timedelta(days=50),
    )
    Role.objects.create(user=expired_user, organization=organization, role="user")

    checkUserExpiration.check_user_expiration()

    audit_log = Log.objects.filter(
        event_type="REMOVED BY INACTIVITY", result="success"
    ).first()
    payload = json.loads(audit_log.payload)

    assert payload["user"]["email"] == "audit_org@example.com"
    assert payload["organization"] == {"name": "Inactive Org"}
    assert "id" not in payload["organization"]


@pytest.mark.django_db(transaction=False, databases=["default", "mini_data_lake"])
def test_check_user_expiration_creates_audit_log_on_deletion_failure(monkeypatch):
    """Test that a failure log entry is written if user deletion raises an error."""
    frozen_now = timezone.now()
    monkeypatch.setattr(checkUserExpiration, "now", lambda: frozen_now)
    monkeypatch.setattr(checkUserExpiration, "send_email", lambda *args, **kwargs: None)

    # Create an expired user target
    expired_user = User.objects.create(
        first_name="Audit",
        last_name="Failure",
        email="audit_fail@example.com",
        last_logged_in=frozen_now - timedelta(days=50),
    )

    # Force user.delete() to raise an error during execution
    def mock_delete_fail(*args, **kwargs):
        raise RuntimeError("Database connection timed out during deletion.")

    monkeypatch.setattr(User, "delete", mock_delete_fail)

    # Run the expiration loop
    checkUserExpiration.check_user_expiration()

    # The user should still exist since delete failed
    assert User.objects.filter(id=expired_user.id).exists()

    # Verify that a failed log payload was created
    failure_log = Log.objects.filter(
        event_type="REMOVED BY INACTIVITY", result="fail"
    ).first()

    assert failure_log is not None

    # Inspect payload for the recorded traceback message
    payload = json.loads(failure_log.payload)
    assert payload["user"]["email"] == "audit_fail@example.com"
    assert "Database connection timed out during deletion." in payload["error"]


@pytest.mark.django_db(transaction=False, databases=["default", "mini_data_lake"])
def test_log_removal_handles_database_write_failures_safely(monkeypatch):
    """Test that log_removal suppresses internal exceptions when writing logs fails."""

    def mock_log_create_fail(*args, **kwargs):
        raise Exception("Log table is marked read-only.")

    monkeypatch.setattr(Log.objects, "create", mock_log_create_fail)

    # Set up a minimal user payload
    user_payload = {
        "id": "123",
        "email": "safe@example.com",
        "full_name": "Safe Test",
        "user_type": UserType.STANDARD,
    }

    # Track if the warning logger was fired
    warning_logged = []
    monkeypatch.setattr(
        checkUserExpiration.LOGGER,
        "warning",
        lambda msg, *args: warning_logged.append(msg % args),
    )

    # Execution should not raise an exception
    try:
        checkUserExpiration.log_removal(user_payload, result="success")
    except Exception as exc:
        pytest.fail(f"log_removal raised an unhandled exception: {exc}")

    # Confirm the warning path caught the error
    assert len(warning_logged) == 1
    assert (
        "Logging error (REMOVED BY INACTIVITY): Log table is marked read-only."
        in warning_logged[0]
    )
