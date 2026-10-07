"""Download PE raw-data Excel exports from S3, zip and encrypt them per-org.

Ported from atc-framework's EC2 CLI script of the same name. Adapted for
a Lambda runtime the same way as download_encrypt_reports.py (direct DB
connection, default credential chain for S3, /tmp-only output).

The original script only processed three hardcoded orgs
(``CSOSA``, ``FRB``, ``EXIM``) rather than every report_on org — that
looks like a one-off/ad hoc restriction rather than the general path, but
is preserved unchanged here since this is a 1:1 port.

Event payload:
    {"report_date": "2026-07-30", "output_dir": "/tmp/pe_reports"}
"""

# Standard Python Libraries
import json
import logging
import os
import shutil

# Third-Party Libraries
import boto3

# Local Libraries
from pe_reports.data.config import db_password_key, reports_bucket_name
from pe_reports.data.db_query import connect, get_orgs, get_orgs_pass
from pe_reports.helpers.pdf_encrypt import encrypt

# Matches the Lambda logging convention established by peScanController.py:
# the root logger, explicitly raised to INFO so CloudWatch actually
# captures our LOGGER.info() calls (Lambda's own default level is WARNING).
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DEFAULT_OUTPUT_DIR = "/tmp/pe_reports"  # nosec B108

# Preserved unchanged from the original script.
_RAW_DATA_ORGS = frozenset({"CSOSA", "FRB", "EXIM"})
_RAW_DATA_FILENAMES = (
    "compromised_credentials.xlsx",
    "domain_alerts.xlsx",
    "mention_incidents.xlsx",
    "vuln_alerts.xlsx",
    "ASM_Summary.xlsx",
)


def download_encrypt_excel(report_date, output_dir):
    """Download each org's raw-data Excel files from S3, zip, then encrypt."""
    bucket = reports_bucket_name()
    s3 = boto3.client("s3")

    pe_orgs = get_orgs(connect())
    os.makedirs(output_dir, exist_ok=True)

    download_count = 0
    for org_code in pe_orgs:
        if org_code == "FAA" or org_code not in _RAW_DATA_ORGS:
            continue

        org_dir = os.path.join(output_dir, org_code)
        os.makedirs(org_dir, exist_ok=True)

        try:
            for file_name in _RAW_DATA_FILENAMES:
                object_name = f"{report_date}/{org_code}-raw-data/{file_name}"
                s3.download_file(bucket, object_name, os.path.join(org_dir, file_name))
                download_count += 1
        except Exception:
            LOGGER.exception("Report is not in S3 for %s", org_code)
            continue

        shutil.make_archive(
            os.path.join(output_dir, f"{org_code}-{report_date}-Raw-Data"),
            format="zip",
            root_dir=org_dir,
        )

    pe_org_pass = get_orgs_pass(connect(), db_password_key())

    encrypt_dir = os.path.join(output_dir, "encrypted_reports")
    os.makedirs(encrypt_dir, exist_ok=True)

    encrypted_count = 0
    for cyhy_db_name, password in pe_org_pass:
        if password is None:
            LOGGER.error("NO PASSWORD for %s", cyhy_db_name)
            continue

        current_file = os.path.join(
            output_dir, f"{cyhy_db_name}-{report_date}-Raw-Data.zip"
        )
        if not os.path.isfile(current_file):
            LOGGER.error("%s report does not exist.", cyhy_db_name)
            continue

        encrypted_org_dir = os.path.join(encrypt_dir, cyhy_db_name)
        os.makedirs(encrypted_org_dir, exist_ok=True)
        encrypted_file = os.path.join(
            encrypted_org_dir, f"{cyhy_db_name}-{report_date}-Raw-Data.zip"
        )

        try:
            encrypt(current_file, password, encrypted_file)
            encrypted_count += 1
        except Exception:
            LOGGER.exception("%s report failed to encrypt.", cyhy_db_name)
            continue

    LOGGER.info("%d downloaded across %d orgs.", download_count, len(pe_orgs))
    LOGGER.info("%d/%d were encrypted.", encrypted_count, len(pe_org_pass))
    return {
        "downloaded": download_count,
        "total_orgs": len(pe_orgs),
        "encrypted": encrypted_count,
    }


def handler(event, context):
    """Lambda entrypoint."""
    try:
        report_date = event["report_date"]
    except KeyError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "report_date is required"}),
        }
    output_dir = event.get("output_dir", DEFAULT_OUTPUT_DIR)
    try:
        result = download_encrypt_excel(report_date, output_dir)
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as exc:
        LOGGER.exception("Unhandled error in download_encrypt_excel")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}
