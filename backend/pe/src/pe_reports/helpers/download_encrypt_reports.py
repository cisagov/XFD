"""Download PE report PDFs from S3 and encrypt them per-org.

Ported from atc-framework's EC2 CLI script of the same name. Adapted for
a Lambda runtime:
  * No SSH tunnel to the database — Lambda runs inside the same VPC and
    connects directly (see pe_reports.data.db_query.connect()).
  * No named AWS profile for S3 — access comes from the Lambda execution
    role's default credential chain.
  * Output goes to /tmp, Lambda's only writable disk, and is not uploaded
    anywhere else. This handler is not wired to a trigger, schedule, or
    IAM policy yet.

Event payload:
    {"report_date": "2026-07-30", "output_dir": "/tmp/pe_reports"}
"""

# Standard Python Libraries
import json
import logging
import os

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


def download_encrypt_reports(report_date, output_dir):
    """Download each report_on org's PDFs from S3, then encrypt them."""
    bucket = reports_bucket_name()
    s3 = boto3.client("s3")

    pe_orgs = get_orgs(connect())
    os.makedirs(output_dir, exist_ok=True)

    download_count = 0
    for org_code in pe_orgs:
        if org_code == "FAA":
            continue

        file_name = f"Posture_and_Exposure_Report-{org_code}-{report_date}.pdf"
        asm_file_name = f"Posture-and-Exposure-ASM-Summary_{org_code}_{report_date}.pdf"
        try:
            s3.download_file(
                bucket,
                f"{report_date}/{file_name}",
                os.path.join(output_dir, file_name),
            )
            s3.download_file(
                bucket,
                f"{report_date}/{asm_file_name}",
                os.path.join(output_dir, asm_file_name),
            )
            download_count += 1
        except Exception:
            LOGGER.exception("Report is not in S3 for %s", org_code)
            continue

    pe_org_pass = get_orgs_pass(connect(), db_password_key())

    encrypt_dir = os.path.join(output_dir, "encrypted_reports")
    os.makedirs(encrypt_dir, exist_ok=True)

    encrypted_count = 0
    for cyhy_db_name, password in pe_org_pass:
        if password is None:
            LOGGER.error("NO PASSWORD for %s", cyhy_db_name)
            continue

        current_file = os.path.join(
            output_dir,
            f"Posture_and_Exposure_Report-{cyhy_db_name}-{report_date}.pdf",
        )
        current_asm_file = os.path.join(
            output_dir,
            f"Posture-and-Exposure-ASM-Summary_{cyhy_db_name}_{report_date}.pdf",
        )
        if not os.path.isfile(current_file):
            LOGGER.error("%s report does not exist.", cyhy_db_name)
            continue
        if not os.path.isfile(current_asm_file):
            LOGGER.error("%s ASM summary does not exist.", cyhy_db_name)
            continue

        encrypted_org_dir = os.path.join(encrypt_dir, cyhy_db_name)
        os.makedirs(encrypted_org_dir, exist_ok=True)

        try:
            encrypt(
                current_file,
                password,
                os.path.join(encrypted_org_dir, os.path.basename(current_file)),
            )
            encrypt(
                current_asm_file,
                password,
                os.path.join(encrypted_org_dir, os.path.basename(current_asm_file)),
            )
            encrypted_count += 1
        except Exception:
            LOGGER.exception("%s report failed to encrypt.", cyhy_db_name)
            continue

    LOGGER.info("%d/%d orgs downloaded.", download_count, len(pe_orgs))
    LOGGER.info("%d/%d orgs encrypted.", encrypted_count, len(pe_org_pass))
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
        result = download_encrypt_reports(report_date, output_dir)
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as exc:
        LOGGER.exception("Unhandled error in download_encrypt_reports")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}
