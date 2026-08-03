"""Encrypt already-downloaded PE report PDFs per-org.

Ported from atc-framework's EC2 CLI script of the same name. Unlike
download_encrypt_reports.py, this script never downloads anything from
S3 — it expects the plain PDFs to already exist under
``{output_dir}/{cyhy_db_name}/...`` (a different, nested layout than
download_encrypt_reports.py's flat one; the two originals were never
meant to share an output_dir). That expectation is preserved as-is from
the original.

The original also printed the decrypted password-key material to stdout
at import time — dropped here, since that's a straightforward secret
leak into logs.

Event payload:
    {"report_date": "2026-07-30", "output_dir": "/tmp/pe_reports"}
"""

# Standard Python Libraries
from datetime import timedelta
import json
import logging
import os
import time

# Third-Party Libraries
from pe_reports.data.config import db_password_key
from pe_reports.data.db_query import connect, get_orgs_pass
from pe_reports.helpers.pdf_encrypt import encrypt

# Matches the Lambda logging convention established by peScanController.py:
# the root logger, explicitly raised to INFO so CloudWatch actually
# captures our LOGGER.info() calls (Lambda's own default level is WARNING).
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DEFAULT_OUTPUT_DIR = "/tmp/pe_reports"  # nosec B108


def encrypt_reports(report_date, output_dir):
    """Encrypt PDFs already present under output_dir/<cyhy_db_name>/."""
    start_time = time.time()

    pe_org_pass = get_orgs_pass(connect(), db_password_key())

    encrypt_dir = os.path.join(output_dir, "encrypted_reports")
    os.makedirs(encrypt_dir, exist_ok=True)

    encrypted_count = 0
    no_pass_count = 0
    LOGGER.info(
        "Encrypting %d PE reports for the %s report run",
        len(pe_org_pass),
        report_date,
    )
    for cyhy_db_name, password in pe_org_pass:
        if password is None:
            LOGGER.warning(
                "No password on file for %s, no encrypted report will be generated",
                cyhy_db_name,
            )
            no_pass_count += 1
            continue

        current_file = os.path.join(
            output_dir,
            cyhy_db_name,
            f"Posture_and_Exposure_Report-{cyhy_db_name}-{report_date}.pdf",
        )
        current_asm_file = os.path.join(
            output_dir,
            cyhy_db_name,
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

    elapsed = timedelta(seconds=time.time() - start_time)
    LOGGER.info(
        "%d/%d reports were encrypted, %d/%d reports have no password",
        encrypted_count,
        len(pe_org_pass),
        no_pass_count,
        len(pe_org_pass),
    )
    LOGGER.info("Execution time for PE report encryption: %s (H:M:S)", elapsed)
    return {
        "encrypted": encrypted_count,
        "no_password": no_pass_count,
        "total": len(pe_org_pass),
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
        result = encrypt_reports(report_date, output_dir)
        return {"statusCode": 200, "body": json.dumps(result)}
    except Exception as exc:
        LOGGER.exception("Unhandled error in encrypt_accessor")
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}
