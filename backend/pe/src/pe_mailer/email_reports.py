"""A module to send Posture and Exposure reports using AWS SES.

Designed to run as a one-shot task inside a Fargate container, either
directly or dispatched from worker/pe_worker.py (SERVICE_TYPE=mailer, one
organization per SQS message). Report PDFs are read from S3 rather than a
local report directory, since Fargate tasks have no persistent/shared
filesystem (see pe_mailer.s3_reports for the bucket/prefix convention).
Retrieval, password-encryption (pe_reports.helpers.pdf_encrypt), and mailing
all happen in this one process/task -- with no shared filesystem between
separate Fargate task invocations, a plaintext PDF written by an earlier,
separate encryption step would never be visible to a later mailing step.

REPORT_DATE is required, the same way pe-reports takes it as a positional
argument (see pe_reports.report_generator) -- reports are stored under a
per-date S3 prefix rather than a per-org one, so there is no per-org prefix
left to scan for a "latest" date the way earlier revisions of this module
did.

Usage:
    pe-mailer REPORT_DATE [--orgs=ORG_LIST] [--summary-to=EMAILS] [--test-emails=EMAILS] [--log-level=LEVEL]

Options:
  -h --help                         Show this message.
  -v --version                      Show version information.
  REPORT_DATE                       Date of the report to mail, format
                                    YYYY-MM-DD. Must match the date prefix
                                    pe-reports uploaded the PDFs under.
  -o --orgs=ORG_LIST                Comma-separated org cyhy_db_name values,
                                    or "all". [default: all]
  -s --summary-to=EMAILS            A comma-separated list of email addresses
                                    to which the summary statistics should be
                                    sent at the end of the run.  If not
                                    specified then no summary will be sent.
  -t --test-emails=EMAILS           A comma-separated list of email addresses
                                    to which to test email send process. If not
                                    specified then no test will be sent.
  -l --log-level=LEVEL              If specified, then the log level will be set to
                                    the specified value.  Valid values are "debug", "info",
                                    "warning", "error", and "critical". [default: info]
"""

# Standard Python Libraries
import datetime
import logging
import os
import shutil
import sys
import tempfile
import time
from typing import Any, Dict

# Third-Party Libraries
import boto3
from botocore.exceptions import ClientError
import docopt
from pe_mailer._version import __version__
from pe_mailer.db import connect, get_org_contacts
from pe_mailer.pe_message import PEMessage
from pe_mailer.s3_reports import (
    asm_summary_object_key,
    download_report_keys,
    object_exists,
    report_object_key,
    upload_encrypted_reports,
)
from pe_mailer.stats_message import StatsMessage
import pe_reports
from pe_reports.data.config import db_password_key
from pe_reports.data.db_query import get_orgs_pass
from pe_reports.helpers.pdf_encrypt import encrypt as encrypt_pdf_file
from pe_source.data.db_query_source import get_orgs
from schema import And, Schema, SchemaError, Use

LOGGER = logging.getLogger(__name__)
MAILER_ARN = os.environ.get("MAILER_ARN")


class UnableToSendError(Exception):
    """Raise when an error is encountered when sending an email.

    Attributes
    ----------
    response : dict
        The response returned by boto3.

    """

    def __init__(self, response):
        """Initialize."""
        self.response = response


def send_message(ses_client, message, counter=None):
    """Send a message.

    Parameters
    ----------
    ses_client : boto3.client
        The boto3 SES client via which the message is to be sent.

    message : email.message.Message
        The email message that is to be sent.

    counter : int
        A counter.

    Returns
    -------
    int: If counter was not None, then counter + 1 is returned if the
    message was sent sent successfully and counter is returned if not.
    If counter was None then None is returned.

    Throws
    ------
    ClientError: If an error is encountered when attempting to send
    the message.

    UnableToSendError: If the response from sending the message is
    anything other than 200.

    """
    # Send Email
    response = ses_client.send_raw_email(RawMessage={"Data": message.as_string()})

    # Check for errors
    status_code = response["ResponseMetadata"]["HTTPStatusCode"]
    if status_code != 200:
        LOGGER.error("Unable to send message. Response from boto3 is: %s", response)
        raise UnableToSendError(response)

    if counter is not None:
        counter += 1

    return counter


def _requested_org_names(orgs_arg):
    """Normalize --orgs values to a set of exact cyhy_db_name matches."""
    if isinstance(orgs_arg, str):
        return {part.strip() for part in orgs_arg.split(",") if part.strip()}
    return set(orgs_arg)


def resolve_orgs(orgs_arg):
    """Return the report_on orgs matching the requested --orgs value.

    Parameters
    ----------
    orgs_arg : str
        Either "all" or a comma-separated list of cyhy_db_name values.

    Returns
    -------
    list(dict): The matching organizations, sorted by cyhy_db_name.

    """
    pe_orgs = get_orgs() or []
    if orgs_arg == "all":
        selected = [org for org in pe_orgs if org.get("report_on")]
    else:
        requested = _requested_org_names(orgs_arg)
        selected = [org for org in pe_orgs if org.get("cyhy_db_name") in requested]

    return sorted(selected, key=lambda org: org.get("cyhy_db_name") or "")


def _load_org_passwords():
    """Return {cyhy_db_name: decrypted_report_password} for every report_on org.

    Uses its own dedicated DB connection, since get_orgs_pass() closes
    whatever connection it's given -- reusing send_pe_reports's own long-
    lived `conn` here would close it out from under the per-org
    get_org_contacts() calls later in that loop.

    Returns
    -------
    dict(str, str): Empty if the DB is unreachable or the password key is
    misconfigured (logged), in which case every org will be treated as
    having no password and skipped rather than mailed unencrypted.

    """
    password_conn = connect()
    if password_conn is None:
        LOGGER.error(
            "Unable to connect to load report encryption passwords; "
            "no reports will be mailed this run"
        )
        return {}

    try:
        return dict(get_orgs_pass(password_conn, db_password_key()))
    except Exception:
        LOGGER.error(
            "Unable to load report encryption passwords; no reports will be "
            "mailed this run",
            exc_info=True,
        )
        return {}


def _encrypt_report_file(path, password, encrypted_dir):
    """Password-encrypt one downloaded report PDF into encrypted_dir.

    Parameters
    ----------
    path : str
        Local path to the plaintext PDF, as downloaded from S3.

    password : str
        The org's report password (from _load_org_passwords()).

    encrypted_dir : str
        Directory (already created) to write the encrypted PDF into. Must
        differ from path's directory -- the PDF library can't save back to
        the file it opened.

    Returns
    -------
    str: Path to the encrypted PDF, using the same basename as path so the
    filename recipients see in the emailed attachment is unchanged.

    """
    encrypted_path = os.path.join(encrypted_dir, os.path.basename(path))
    encrypt_pdf_file(path, password, encrypted_path)
    return encrypted_path


def send_pe_reports(ses_client, s3_client, s3_bucket, report_date, orgs, to):
    """Send out Posture and Exposure reports for the given orgs.

    Parameters
    ----------
    ses_client : boto3.client
        The boto3 SES client via which the message is to be sent.

    s3_client : boto3.client
        The boto3 S3 client used to download report PDFs.

    s3_bucket : str
        The S3 bucket containing generated report PDFs.

    report_date : str
        The report date ("YYYY-MM-DD") pe-reports uploaded PDFs under --
        the S3 date prefix to read from for every org.

    orgs : list(dict)
        The organizations (as returned by resolve_orgs()) to mail
        reports to.

    to : list(str) or None
        If given, overrides each org's contact-derived recipients with
        this fixed list of addresses (used for --test-emails runs).

    Returns
    -------
    str: A string that summarizes what was sent, or None if no
    organizations were found for the requested --orgs value.

    """
    conn = connect()
    org_passwords = _load_org_passwords()

    agencies_emailed_pe_reports = 0
    reports_not_mailed = 0

    for org in orgs:
        cyhy_id = org.get("cyhy_db_name")
        if not cyhy_id:
            continue

        if cyhy_id == "GSEC":
            LOGGER.warning(
                "The PDF report for %s was intentionally set to not be mailed",
                cyhy_id,
            )
            reports_not_mailed += 1
            continue

        if to is not None:
            to_emails = to
        elif conn is not None:
            contact_dict = get_org_contacts(conn, cyhy_id)
            to_emails = contact_dict["DISTRO"] or contact_dict["TECHNICAL"]
        else:
            to_emails = []

        # to_emails should contain at least one email
        if not to_emails:
            LOGGER.warning(
                "No contacts found for %s, no report will be mailed", cyhy_id
            )
            reports_not_mailed += 1
            continue

        # Reports live under a per-date S3 prefix (matching
        # pe_reports.report_generator.upload_file_to_s3), so the key is
        # built directly from report_date rather than discovered by
        # scanning -- see pe_mailer.s3_reports for the convention.
        report_key = report_object_key(report_date, cyhy_id)
        asm_key = asm_summary_object_key(report_date, cyhy_id)

        if not object_exists(s3_client, s3_bucket, report_key):
            LOGGER.warning(
                "No report PDF found at s3://%s/%s, no report will be mailed",
                s3_bucket,
                report_key,
            )
            reports_not_mailed += 1
            continue

        if not object_exists(s3_client, s3_bucket, asm_key):
            LOGGER.warning(
                "No ASM summary PDF found for %s dated %s, sending report "
                "without an ASM summary",
                cyhy_id,
                report_date,
            )
            asm_key = None

        password = org_passwords.get(cyhy_id)
        if not password:
            LOGGER.warning(
                "No report encryption password found for %s, no report "
                "will be mailed",
                cyhy_id,
            )
            reports_not_mailed += 1
            continue

        tmp_dir = tempfile.mkdtemp(prefix="pe-mailer-")
        try:
            keys_to_download = [report_key] + ([asm_key] if asm_key else [])
            local_paths = download_report_keys(
                s3_client, s3_bucket, keys_to_download, tmp_dir
            )
            plaintext_report_path = local_paths[0]
            plaintext_asm_path = local_paths[1] if asm_key else None

            # Encrypt into a separate subdirectory (the PDF library can't
            # save back to the file it opened) using each attachment's
            # original basename, so the filename recipients see is
            # unchanged from before encryption was added.
            encrypted_dir = os.path.join(tmp_dir, "encrypted")
            os.makedirs(encrypted_dir, exist_ok=True)
            pe_report_filename = _encrypt_report_file(
                plaintext_report_path, password, encrypted_dir
            )
            pe_asm_filename = (
                _encrypt_report_file(plaintext_asm_path, password, encrypted_dir)
                if plaintext_asm_path
                else None
            )

            # Persist the encrypted PDFs to S3 (<report_date>/encrypted-reports/,
            # alongside the plaintext originals for that same date -- see
            # s3_reports.py) so an already-encrypted copy is retrievable
            # without redoing the encryption step. Best-effort: a failed
            # upload shouldn't stop the report from being emailed.
            try:
                upload_encrypted_reports(
                    s3_client,
                    s3_bucket,
                    report_date,
                    [pe_report_filename]
                    + ([pe_asm_filename] if pe_asm_filename else []),
                )
            except ClientError:
                LOGGER.error(
                    "Unable to upload encrypted report(s) to S3 for %s",
                    cyhy_id,
                    exc_info=True,
                    stack_info=True,
                )

            human_report_date = datetime.datetime.strptime(
                report_date, "%Y-%m-%d"
            ).strftime("%B %d, %Y")

            # Construct the Posture and Exposure message to send
            message = PEMessage(
                pe_report_filename,
                pe_asm_filename,
                human_report_date,
                cyhy_id,
                to_emails,
            )

            LOGGER.info("Recipient(s): %s", to_emails)
            LOGGER.info("Report date: %s", human_report_date)
            LOGGER.info("Report file: %s", pe_report_filename)
            LOGGER.info("ASM summary file: %s", pe_asm_filename)

            try:
                agencies_emailed_pe_reports = send_message(
                    ses_client, message, agencies_emailed_pe_reports
                )
            except (UnableToSendError, ClientError):
                LOGGER.error(
                    "Unable to send Posture and Exposure report for agency with ID %s",
                    cyhy_id,
                    exc_info=True,
                    stack_info=True,
                )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if conn is not None:
        conn.close()

    total_orgs = len(orgs)
    if total_orgs == 0:
        LOGGER.critical("No organizations were found for the requested --orgs value")
        return None

    # Print out and log some statistics
    pe_stats_string = (
        f"Out of {total_orgs} agencies with Posture and Exposure reports, "
        f"{agencies_emailed_pe_reports} "
        f"({100.0 * agencies_emailed_pe_reports / total_orgs:.2f}%) were emailed."
    )
    mail_summary_log_string = (
        f"{agencies_emailed_pe_reports}/{total_orgs} reports were mailed, "
        f"{reports_not_mailed}/{total_orgs} reports were not mailed"
    )
    LOGGER.info(mail_summary_log_string)

    return pe_stats_string


def send_reports(report_date, orgs_arg, summary_to, test_emails):
    """Send emails."""
    # Matches the Terraform-provisioned env var name (infrastructure/pe_worker.tf,
    # peReportController.py) -- not pe_reports.data.config.reports_bucket_name()'s
    # PE_REPORTS_BUCKET_NAME, which nothing in this deployment actually sets.
    s3_bucket = os.environ.get("REPORTS_BUCKET_NAME")
    if not s3_bucket:
        LOGGER.critical("REPORTS_BUCKET_NAME is not set. Exiting.")
        sys.exit(1)

    if not MAILER_ARN:
        LOGGER.critical("MAILER_ARN is not set. Exiting.")
        sys.exit(1)

    # Assume role to use mailer. The default boto3 credential chain
    # resolves to the Fargate task role, which must be allowed to assume
    # MAILER_ARN.
    sts_client = boto3.client("sts")
    assumed_role_object = sts_client.assume_role(
        RoleArn=MAILER_ARN, RoleSessionName="AssumeRoleSession1"
    )
    credentials = assumed_role_object["Credentials"]

    ses_client = boto3.client(
        "ses",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    # Reading generated reports from S3 uses the task's own role directly;
    # no cross-account assume-role is needed for that.
    s3_client = boto3.client("s3")

    orgs = resolve_orgs(orgs_arg)

    # Email the summary statistics, if necessary
    if test_emails is not None:
        to = test_emails.split(",")
    else:
        to = None

    # Send reports and gather summary statistics
    stats = send_pe_reports(ses_client, s3_client, s3_bucket, report_date, orgs, to)

    # Email the summary statistics, if necessary
    if summary_to is not None and stats:
        message = StatsMessage(summary_to.split(","), stats)
        try:
            send_message(ses_client, message)
        except (UnableToSendError, ClientError):
            LOGGER.error(
                "Unable to send pe-mailer report summary",
                exc_info=True,
                stack_info=True,
            )
    elif stats is None:
        LOGGER.warning("Nothing was emailed.")


def main():
    """Send emails."""
    LOGGER.info("--- PE Report Mailing Starting ---")
    start_time = time.time()
    # Parse command line arguments
    args: Dict[str, str] = docopt.docopt(__doc__, version=__version__)

    # Validate and convert arguments
    schema: Schema = Schema(
        {
            "--log-level": And(
                str,
                Use(str.lower),
                lambda n: n in ("debug", "info", "warning", "error", "critical"),
                error="Possible values for --log-level are "
                + "debug, info, warning, error, and critical.",
            ),
            str: object,  # Don't care about other keys, if any
        }
    )

    try:
        validated_args: Dict[str, Any] = schema.validate(args)
    except SchemaError as err:
        # Exit because one or more of the arguments were invalid. Logging
        # isn't configured yet at this point, so write directly to stderr
        # (matches pe_source.pe_scripts's equivalent argument-validation
        # failure).
        sys.stderr.write("{}\n".format(err))
        sys.exit(1)

    # Assign validated arguments to variables
    log_level: str = validated_args["--log-level"]

    # Setup logging. In Fargate, PE_LOG_TO_STDERR=1 additionally streams
    # logs to stderr so they reach the awslogs driver / CloudWatch Logs,
    # matching the convention used by pe_source.pe_scripts.
    logging.basicConfig(
        filename=pe_reports.CENTRAL_LOGGING_FILE,
        filemode="a",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S",
        level=log_level.upper(),
    )
    if os.getenv("PE_LOG_TO_STDERR", "").lower() in {"1", "true", "yes"}:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%m/%d/%Y %I:%M:%S",
            )
        )
        logging.getLogger().addHandler(stderr_handler)

    LOGGER.info("Posture & Exposure Report Mailer, Version : %s", __version__)

    send_reports(
        validated_args["REPORT_DATE"],
        validated_args["--orgs"],
        validated_args["--summary-to"],
        validated_args["--test-emails"],
    )

    end_time = time.time()
    LOGGER.info(
        f"Execution time for PE report mailing: {str(datetime.timedelta(seconds=(end_time - start_time)))} (H:M:S)"
    )
    LOGGER.info("--- PE Report Mailing Complete ---")

    # Stop logging and clean up
    logging.shutdown()


if __name__ == "__main__":
    main()
