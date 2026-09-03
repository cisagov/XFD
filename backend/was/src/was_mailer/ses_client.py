"""Create an isolated SES client with refreshable cross-account credentials."""

import boto3
from botocore.client import BaseClient
from botocore.credentials import (
    AssumeRoleCredentialFetcher,
    CredentialProvider,
    CredentialResolver,
    DeferredRefreshableCredentials,
)
from botocore.exceptions import NoCredentialsError
from botocore.session import Session

from was_reports.utils.env import getenv


class SesRoleProvider(CredentialProvider):
    """Resolve SES role credentials without altering the default AWS session."""

    METHOD = "assume-role"

    def __init__(self, source_session: boto3.Session, role_arn: str) -> None:
        """Retain the source credential chain and destination role."""
        self.source_session = source_session
        self.role_arn = role_arn

    def load(self) -> DeferredRefreshableCredentials:
        """Defer STS calls and refresh expiring credentials through botocore."""
        source_credentials = self.source_session.get_credentials()
        if source_credentials is None:
            raise NoCredentialsError()
        fetcher = AssumeRoleCredentialFetcher(
            client_creator=self.source_session.client,
            source_credentials=source_credentials,
            role_arn=self.role_arn,
            extra_args={"RoleSessionName": "was-reporting"},
        )
        return DeferredRefreshableCredentials(
            refresh_using=fetcher.fetch_credentials,
            method=self.METHOD,
        )


def create_ses_client() -> BaseClient:
    """Use an optional SES role, never fall back after an assumption failure."""
    role_arn = (getenv("WAS_SES_ROLE_ARN") or "").strip()
    source_session = boto3.Session()
    if not role_arn:
        return source_session.client("ses")
    arn_parts = role_arn.split(":", 5)
    if (
        len(arn_parts) != 6
        or arn_parts[0] != "arn"
        or arn_parts[2] != "iam"
        or arn_parts[3]
        or len(arn_parts[4]) != 12
        or not arn_parts[4].isdigit()
        or not arn_parts[5].startswith("role/")
        or not arn_parts[5][5:]
    ):
        raise ValueError("WAS_SES_ROLE_ARN must be an IAM role ARN.")
    role_session = Session()
    role_session.register_component(
        "credential_provider",
        CredentialResolver([SesRoleProvider(source_session, role_arn)]),
    )
    return boto3.Session(botocore_session=role_session).client(
        "ses", region_name=source_session.region_name
    )
