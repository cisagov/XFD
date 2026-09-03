"""Test isolated SES role assumption without making AWS requests."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import MagicMock, patch

from botocore.credentials import Credentials
from botocore.exceptions import ClientError, NoCredentialsError

from was_mailer.ses_client import SesRoleProvider, create_ses_client

ROLE_ARN = "arn:aws:iam::123456789012:role/test-ses"


class SesClientTests(unittest.TestCase):
    """Cover role configuration, refresh, failures, and session isolation."""

    def test_default_credentials_without_role(self) -> None:
        """Keep direct SES delivery available when no role is configured."""
        with patch("was_mailer.ses_client.getenv", return_value=""), patch(
            "was_mailer.ses_client.boto3.Session"
        ) as session_factory:
            client = create_ses_client()
        session_factory.return_value.client.assert_called_once_with("ses")
        self.assertIs(client, session_factory.return_value.client.return_value)

    def test_invalid_role_rejected(self) -> None:
        """Reject malformed role configuration before creating a client."""
        with patch("was_mailer.ses_client.getenv", return_value="replace-me"), patch(
            "was_mailer.ses_client.boto3.Session"
        ) as session_factory:
            with self.assertRaises(ValueError):
                create_ses_client()
        session_factory.return_value.client.assert_not_called()

    def test_separate_session_for_ses(self) -> None:
        """Register role credentials only in the new SES session."""
        source_session = MagicMock()
        source_session.region_name = "us-east-1"
        destination_session = MagicMock()
        with patch("was_mailer.ses_client.getenv", return_value=ROLE_ARN), patch(
            "was_mailer.ses_client.boto3.Session",
            side_effect=[source_session, destination_session],
        ), patch("was_mailer.ses_client.Session") as core_session:
            create_ses_client()
        source_session.client.assert_not_called()
        core_session.return_value.register_component.assert_called_once()
        destination_session.client.assert_called_once_with(
            "ses", region_name="us-east-1"
        )

    def test_credentials_refresh_and_fail_closed(self) -> None:
        """Refresh expiring credentials and propagate denied assumptions."""
        source_session = MagicMock()
        source_session.get_credentials.return_value = Credentials(
            "test-source-key", "test-source-secret", "test-source-token"
        )
        expiration = datetime.now(timezone.utc) + timedelta(minutes=5)
        response = {
            "Credentials": {
                "AccessKeyId": "test-assumed-key",
                "SecretAccessKey": "test-assumed-secret",
                "SessionToken": "test-assumed-token",
                "Expiration": expiration,
            },
            "AssumedRoleUser": {"Arn": ROLE_ARN, "AssumedRoleId": "test"},
        }
        denied = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "AssumeRole",
        )
        assume_role = source_session.client.return_value.assume_role
        assume_role.side_effect = [response, response, denied]
        credentials = SesRoleProvider(source_session, ROLE_ARN).load()
        assume_role.assert_not_called()
        self.assertEqual(
            credentials.get_frozen_credentials().access_key, "test-assumed-key"
        )
        credentials.get_frozen_credentials()
        self.assertEqual(assume_role.call_count, 2)
        with self.assertRaises(ClientError):
            credentials.get_frozen_credentials()
        assume_role.assert_called_with(
            RoleArn=ROLE_ARN, RoleSessionName="was-reporting"
        )

    def test_missing_source_credentials(self) -> None:
        """Fail clearly rather than creating an unsigned SES client."""
        source_session = MagicMock()
        source_session.get_credentials.return_value = None
        with self.assertRaises(NoCredentialsError):
            SesRoleProvider(source_session, ROLE_ARN).load()


if __name__ == "__main__":
    unittest.main()
