"""Helpers for reading generated P&E report PDFs out of S3.

Fargate tasks have no shared/persistent local disk, so report PDFs
produced by the (not yet migrated) report-generation side are expected to
land in S3 rather than a local directory. The convention mirrors the old
local layout 1:1: objects are stored under a per-org prefix named for the
org's cyhy_db_name, e.g.:

    s3://<BUCKET>/<cyhy_db_name>/Posture_and_Exposure_Report-2026-07-30.pdf
    s3://<BUCKET>/<cyhy_db_name>/Posture-and-Exposure-ASM-Summary-2026-07-30.pdf

Password-encrypted copies (built in-process from those plaintext PDFs, see
pe_mailer.email_reports) are uploaded back under a separate top-level
ENCRYPTED_PREFIX, deliberately outside the "<cyhy_db_name>/" prefix that
select_latest_report_keys() scans -- keeping them under the org prefix
would let a later run's date/basename matching pick an already-encrypted
PDF back up as though it were that cycle's plaintext source:

    s3://<BUCKET>/encrypted-reports/<cyhy_db_name>/Posture_and_Exposure_Report-2026-07-30.pdf
"""

# Standard Python Libraries
import logging
import os
import re

LOGGER = logging.getLogger(__name__)

# Matches the two report-file naming conventions described above, e.g.
# "Posture_and_Exposure_Report-2026-07-30.pdf" or
# "Posture-and-Exposure-ASM-Summary-2026-07-30.pdf".
REPORT_FILENAME_RE = re.compile(
    r"^Posture_and_Exposure_Report-(?P<date>\d{4}-[01]\d-[0-3]\d)\.pdf$",
    re.IGNORECASE,
)
ASM_SUMMARY_FILENAME_RE = re.compile(
    r"^Posture-and-Exposure-ASM-Summary-(?P<date>\d{4}-[01]\d-[0-3]\d)\.pdf$",
    re.IGNORECASE,
)

# Top-level prefix for password-encrypted report/ASM-summary copies -- see the
# module docstring for why this must not sit under the "<cyhy_db_name>/" prefix.
ENCRYPTED_PREFIX = "encrypted-reports"


def select_latest_report_keys(s3_client, bucket, cyhy_db_name):
    """Return the most recent, date-matched report/ASM summary S3 keys.

    Lists every .pdf object key under the org's S3 prefix and groups them by
    the report date embedded in each filename, then returns the single most
    recent date's keys -- rather than returning every historical PDF and
    letting the caller pick a report and an ASM summary independently, which
    can select mismatched dates (e.g. this cycle's report paired with a
    leftover ASM summary from a prior cycle).

    Parameters
    ----------
    s3_client : boto3.client
        A boto3 S3 client.

    bucket : str
        The S3 bucket containing the generated reports.

    cyhy_db_name : str
        The organization's cyhy_db_name, used as the S3 prefix.

    Returns
    -------
    tuple(str or None, str or None, str or None): (report_key, asm_key,
    report_date) where report_date is a "YYYY-MM-DD" string shared by both
    keys. report_key is None if no report PDF was found for this org at
    all. asm_key is None if no ASM summary PDF exists for report_key's date.

    """
    prefix = f"{cyhy_db_name}/"
    keys_by_date: dict = {}
    extra_keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(".pdf"):
                continue
            filename = os.path.basename(key)

            match = REPORT_FILENAME_RE.match(filename)
            if match:
                keys_by_date.setdefault(match.group("date"), {})["report"] = key
                continue

            match = ASM_SUMMARY_FILENAME_RE.match(filename)
            if match:
                keys_by_date.setdefault(match.group("date"), {})["asm"] = key
                continue

            extra_keys.append(key)

    for key in extra_keys:
        LOGGER.error("Extra PDF file or named incorrectly: %s", key)

    dates_with_report = [d for d, files in keys_by_date.items() if "report" in files]
    if not dates_with_report:
        return None, None, None

    latest_date = max(dates_with_report)
    latest_files = keys_by_date[latest_date]
    return latest_files.get("report"), latest_files.get("asm"), latest_date


def download_report_keys(s3_client, bucket, keys, dest_dir):
    """Download the given S3 keys into dest_dir and return local paths.

    Parameters
    ----------
    s3_client : boto3.client
        A boto3 S3 client.

    bucket : str
        The S3 bucket containing the generated reports.

    keys : list(str)
        The object keys to download.

    dest_dir : str
        A local directory (already created) to download files into.

    Returns
    -------
    list(str): Local filesystem paths, in the same order as keys.

    """
    local_paths = []
    for key in keys:
        filename = os.path.basename(key)
        local_path = os.path.join(dest_dir, filename)
        s3_client.download_file(bucket, key, local_path)
        LOGGER.debug("Downloaded s3://%s/%s to %s", bucket, key, local_path)
        local_paths.append(local_path)

    return local_paths


def upload_encrypted_reports(s3_client, bucket, cyhy_db_name, local_paths):
    """Upload password-encrypted PDFs to S3 under ENCRYPTED_PREFIX/<cyhy_db_name>/.

    Parameters
    ----------
    s3_client : boto3.client
        A boto3 S3 client.

    bucket : str
        The S3 bucket to upload the encrypted PDFs to.

    cyhy_db_name : str
        The organization's cyhy_db_name, used as the destination sub-prefix.

    local_paths : list(str)
        Local filesystem paths to the already-encrypted PDFs (as written by
        pe_reports.helpers.pdf_encrypt.encrypt), keeping their basenames on
        upload.

    Returns
    -------
    list(str): The S3 keys uploaded to, in the same order as local_paths.

    """
    uploaded_keys = []
    for local_path in local_paths:
        filename = os.path.basename(local_path)
        key = f"{ENCRYPTED_PREFIX}/{cyhy_db_name}/{filename}"
        s3_client.upload_file(local_path, bucket, key)
        LOGGER.debug("Uploaded %s to s3://%s/%s", local_path, bucket, key)
        uploaded_keys.append(key)

    return uploaded_keys
