"""Email methods."""
# Standard Python Libraries
import logging
import os

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError
from botocore.session import Session as BotoCoreSession
from django.conf import settings
from jinja2 import Template

from .s3_client import S3Client

# Configure logging
LOGGER = logging.getLogger(__name__)
IS_DMZ = os.getenv("IS_DMZ", "0") == "1"


def ensure_zscaler_cert_downloaded():
    """Ensure zscaler cert downloaded."""
    cert_path = "/tmp/zscaler.pem"  # nosec B108
    if not os.path.exists(cert_path):
        s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-gov-east-1"))
        s3.download_file(
            os.getenv("ZSCALER_CERT_BUCKET_NAME", "cisa-crossfeed-prod-zscaler"),
            "zscaler.pem",
            cert_path,
        )
    return cert_path


def send_invite_email(email, organization=None):
    """Send an invitation email to the specified address."""
    frontend_domain = settings.FRONTEND_DOMAIN
    reply_to = settings.CROSSFEED_SUPPORT_EMAIL_REPLYTO

    org_name_part = (
        "the {} organization on ".format(organization.name) if organization else ""
    )
    message = """
    Hi there,

    You've been invited to join {org_name_part}CyHy Dashboard. To accept the invitation and start using CyHy Dashboard, sign on at {frontend_domain}/signup.

    CyHy Dashboard access instructions:

    1. Visit {frontend_domain}/signup.
    2. Select "Create Account."
    3. Enter your email address and a new password for CyHy Dashboard.
    4. A confirmation code will be sent to your email. Enter this code when you receive it.
    5. You will be prompted to enable MFA. Scan the QR code with an authenticator app on your phone, such as Microsoft Authenticator. Enter the MFA code you see after scanning.
    6. After configuring your account, you will be redirected to CyHy Dashboard.

    For more information on using CyHy Dashboard, view the CyHy Dashboard user guide at https://docs.crossfeed.cyber.dhs.gov/user-guide/quickstart/.

    If you encounter any difficulties, please feel free to reply to this email (or send an email to {reply_to}).
    """.format(
        org_name_part=org_name_part, frontend_domain=frontend_domain, reply_to=reply_to
    )
    send_email(email, "CyHy Dashboard Invitation", message)


def send_email(recipient, subject, body):
    """Send an email using AWS SES."""
    if not IS_DMZ:
        session = BotoCoreSession()
        session.set_config_variable("ca_bundle", ensure_zscaler_cert_downloaded())
    ses_client = boto3.client("ses", region_name=os.getenv("EMAIL_REGION"))
    sender = settings.CROSSFEED_SUPPORT_EMAIL_SENDER
    reply_to = settings.CROSSFEED_SUPPORT_EMAIL_REPLYTO

    email_params = {
        "Source": sender,
        "Destination": {"ToAddresses": [recipient]},
        "Message": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}},
        "ReplyToAddresses": [reply_to],
    }

    try:
        ses_client.send_email(**email_params)
        LOGGER.info("Email sent to %s", recipient)
    except ClientError as e:
        LOGGER.error("Error sending email: %s", e)


def send_registration_approved_email(
    recipient: str, subject: str, first_name: str, last_name: str, template
):
    """Send registration approved email."""
    try:
        # Initialize S3 client and fetch email template
        client = S3Client()
        html_template = client.get_email_asset(template)

        if not html_template:
            raise ValueError("Email template not found or empty.")

        # Set up the email content with Jinja2 template rendering
        template = Template(html_template)
        data = {
            "firstName": first_name,
            "lastName": last_name,
            "domain": settings.FRONTEND_DOMAIN,
        }
        html_to_send = template.render(data)

        # Email configuration
        sender = settings.CROSSFEED_SUPPORT_EMAIL_SENDER
        reply_to = settings.CROSSFEED_SUPPORT_EMAIL_REPLYTO

        email_params = {
            "Source": sender,
            "Destination": {"ToAddresses": [recipient]},
            "Message": {
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html_to_send}},
            },
            "ReplyToAddresses": [reply_to],
        }
        # SES client
        if not IS_DMZ:
            session = BotoCoreSession()
            session.set_config_variable("ca_bundle", ensure_zscaler_cert_downloaded())
        if not settings.IS_LOCAL:
            ses_client = boto3.client("ses", region_name=os.getenv("EMAIL_REGION"))
            # Send email
            ses_client.send_email(**email_params)
            LOGGER.info(
                "Email sent successfully | From: %s | To: %s", sender, recipient
            )
        else:
            # TODO: Determine if we need this condition for local env
            LOGGER.info(
                "Email not attempted for local env | From: %s | To: %s",
                sender,
                recipient,
            )

    except (ClientError, ValueError) as e:
        LOGGER.error("Email failed with error: %s", e)


def send_registration_denied_email(
    recipient: str, subject: str, first_name: str, last_name: str, template
):
    """Send registration denied email."""
    try:
        # Initialize S3 client and fetch email template
        client = S3Client()
        html_template = client.get_email_asset(template)

        if not html_template:
            raise ValueError("Email template not found or empty.")

        # Set up the email content with Jinja2 template rendering
        template = Template(html_template)
        data = {
            "firstName": first_name,
            "lastName": last_name,
        }
        html_to_send = template.render(data)

        # Email configuration
        sender = settings.CROSSFEED_SUPPORT_EMAIL_SENDER
        reply_to = settings.CROSSFEED_SUPPORT_EMAIL_REPLYTO

        email_params = {
            "Source": sender,
            "Destination": {"ToAddresses": [recipient]},
            "Message": {
                "Subject": {"Data": subject},
                "Body": {"Html": {"Data": html_to_send}},
            },
            "ReplyToAddresses": [reply_to],
        }
        # SES client
        if not settings.IS_LOCAL:
            if not IS_DMZ:
                session = BotoCoreSession()
                session.set_config_variable(
                    "ca_bundle", ensure_zscaler_cert_downloaded()
                )
            ses_client = boto3.client("ses", region_name=os.getenv("EMAIL_REGION"))
            # Send email
            ses_client.send_email(**email_params)
            LOGGER.info(
                "Email sent successfully | From: %s | To: %s", sender, recipient
            )
        else:
            # TODO: Determine if we need this condition for local env
            LOGGER.info(
                "Email not attempted for local env | From: %s | To: %s",
                sender,
                recipient,
            )

    except (ClientError, ValueError) as e:
        LOGGER.error("Email failed with error: %s", e)
