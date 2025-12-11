"""Tests for checkUserExpiration Lambda task."""
# Standard Python Libraries
from datetime import timedelta

# Third-Party Libraries
from django.utils import timezone
import pytest
from xfd_api.tasks import checkUserExpiration
from xfd_mini_dl.models import User


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_check_user_expiration_sends_emails_and_deletes(monkeypatch):
    """Users in each inactivity band get the right email behavior and 90+ day users are deleted."""
    # Freeze "now" in the task module
    frozen_now = timezone.now()

    # Patch the now() used inside checkUserExpiration
    monkeypatch.setattr(checkUserExpiration, "now", lambda: frozen_now)

    # Capture emails instead of actually sending
    emails_sent = []

    def fake_send_email(to_addr, subject, body):
        emails_sent.append({"to": to_addr, "subject": subject, "body": body})

    monkeypatch.setattr(checkUserExpiration, "send_email", fake_send_email)

    # Create users in different inactivity windows
    # 20 days inactive -> should get NO email
    user_20 = User.objects.create(
        first_name="Twenty",
        last_name="Days",
        email="20@example.com",
        last_logged_in=frozen_now - timedelta(days=20),
    )

    # 35 days inactive -> 30-day notice
    user_35 = User.objects.create(
        first_name="ThirtyFive",
        last_name="Days",
        email="35@example.com",
        last_logged_in=frozen_now - timedelta(days=35),
    )

    # 60 days inactive -> 45-day notice
    user_60 = User.objects.create(
        first_name="Sixty",
        last_name="Days",
        email="60@example.com",
        last_logged_in=frozen_now - timedelta(days=60),
    )

    # 120 days inactive -> 90-day notice + deletion
    user_120 = User.objects.create(
        first_name="OneTwenty",
        last_name="Days",
        email="120@example.com",
        last_logged_in=frozen_now - timedelta(days=120),
    )

    # Run the task
    checkUserExpiration.check_user_expiration()

    # Reload from DB / assert existence or deletion
    assert User.objects.filter(id=user_20.id).exists()  # recent user should remain
    assert User.objects.filter(id=user_35.id).exists()  # 30–45 day user should remain
    assert User.objects.filter(id=user_60.id).exists()  # 45–90 day user should remain
    assert not User.objects.filter(
        id=user_120.id
    ).exists()  # 90+ day user should be deleted

    # Verify emails
    # We expect 3 emails: one for 35-day, one for 60-day, one for 120-day
    assert len(emails_sent) == 3

    # Get emails by recipient to make assertions easier
    emails_by_to = {e["to"]: e for e in emails_sent}

    # 20-day user should not receive an email
    assert "20@example.com" not in emails_by_to

    # 30–45 day user should get inactivity notice
    assert "35@example.com" in emails_by_to
    assert emails_by_to["35@example.com"]["subject"] == "Account Inactivity Notice"
    assert "inactive for over 30 days" in emails_by_to["35@example.com"]["body"]

    # 45–90 day user should get deactivation notice
    assert "60@example.com" in emails_by_to
    assert emails_by_to["60@example.com"]["subject"] == "Account Deactivation Notice"
    assert "inactive for over 45 days" in emails_by_to["60@example.com"]["body"]

    # 90+ day user should get removal notice
    assert "120@example.com" in emails_by_to
    assert emails_by_to["120@example.com"]["subject"] == "Account Removal Notice"
    assert (
        "inactive for over 90 days and has been removed"
        in emails_by_to["120@example.com"]["body"]
    )


def test_handler_success(monkeypatch):
    """Handler should call check_user_expiration and return 200 on success."""
    called = {"count": 0}

    def fake_check():
        called["count"] += 1

    monkeypatch.setattr(checkUserExpiration, "check_user_expiration", fake_check)

    response = checkUserExpiration.handler(event={}, context={})

    assert called["count"] == 1
    assert response["status_code"] == 200
    assert "completed successfully" in response["body"]


def test_handler_failure(monkeypatch):
    """Handler should return 500 when check_user_expiration raises."""

    def fake_check():
        raise RuntimeError("boom")

    monkeypatch.setattr(checkUserExpiration, "check_user_expiration", fake_check)

    response = checkUserExpiration.handler(event={}, context={})

    assert response["status_code"] == 500
    assert "boom" in response["body"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_handler_test_mode_staging_creates_and_deletes_user(monkeypatch):
    """In staging, Test=true should create a user, run 30/45/90 flow, send emails, and delete the user."""
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

    # User should have been created and then deleted
    assert not User.objects.filter(email="uat@example.com").exists()

    # Should have sent 3 emails (30, 45, 90)
    assert len(emails) == 3
    subjects = {e["subject"] for e in emails}
    assert "Account Inactivity Notice" in subjects
    assert "Account Deactivation Notice" in subjects
    assert "Account Removal Notice" in subjects


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_handler_test_mode_existing_email_raises(monkeypatch):
    """If the test email already exists, handler should return 500."""
    monkeypatch.setenv("STAGE", "staging")

    # Create an existing user with that email
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

    # Because _run_test_expiration_flow raises, handler returns 500
    assert response["status_code"] == 500
    assert "already exists" in response["body"]
    # No test emails should have been sent
    assert not emails


def test_handler_test_mode_forbidden_when_not_staging(monkeypatch):
    """When STAGE!=staging, Test=true should return 403 and not run the flow."""
    monkeypatch.setenv("STAGE", "production")

    called = {"count": 0}

    def fake_check():
        called["count"] += 1

    # Ensure normal path isn't accidentally called for Test=true
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
