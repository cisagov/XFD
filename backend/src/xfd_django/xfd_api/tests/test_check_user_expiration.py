"""Tests for checkUserExpiration Lambda task."""
# Standard Python Libraries
from datetime import timedelta

# Third-Party Libraries
from django.utils import timezone
import pytest
from xfd_api.tasks import checkUserExpiration
from xfd_mini_dl.models import User


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
    assert by_to["60@example.com"][0]["subject"] == "Account Deactivation Notice"
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
    assert emails_sent == []


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
    assert "Account Deactivation Notice" in subjects


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
