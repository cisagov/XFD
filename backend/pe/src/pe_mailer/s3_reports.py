"""Helpers for reading generated P&E report PDFs out of S3.

Fargate tasks have no shared/persistent local disk, so report PDFs
produced by pe_reports.report_generator are expected to land in S3 rather
than a local directory. The convention matches report_generator's own
upload_file_to_s3() 1:1 (and the (unwired) download_encrypt_reports.py /
download_encrypt_excel.py Lambdas, which read the same layout): objects are
stored under a per-run date prefix, with each org's cyhy_db_name and the
report date embedded in the filename, e.g.:

    s3://<BUCKET>/2026-07-30/Posture_and_Exposure_Report-DHS-2026-07-30.pdf
    s3://<BUCKET>/2026-07-30/Posture-and-Exposure-ASM-Summary_DHS_2026-07-30.pdf

Because the date prefix (not the org) is the top-level folder, pe-mailer is
given the report date explicitly (--report-date, threaded down from
peMailerController same as pe-reports gets it) rather than discovering it
by listing -- there is no per-org prefix left to scan.

Password-encrypted copies (built in-process from those plaintext PDFs, see
pe_mailer.email_reports) are uploaded back under an ENCRYPTED_PREFIX
sub-folder *within that same date folder*, alongside the plaintext
originals, keeping everything for one report run under one date prefix:

    s3://<BUCKET>/2026-07-30/encrypted-reports/Posture_and_Exposure_Report-DHS-2026-07-30.pdf
"""

# Standard Python Libraries
import logging
import os

LOGGER = logging.getLogger(__name__)

# Sub-prefix, within a date folder, for password-encrypted report/ASM-summary
# copies -- see the module docstring.
ENCRYPTED_PREFIX = "encrypted-reports"


def report_object_key(report_date, cyhy_db_name):
    """Return the S3 key of an org's plaintext report PDF.

    Matches the filename report_generator.py writes at
    ``{output_directory}/{org_code}/Posture_and_Exposure_Report-{org_code}-{datestring}.pdf``.
    """
    return f"{report_date}/Posture_and_Exposure_Report-{cyhy_db_name}-{report_date}.pdf"


def asm_summary_object_key(report_date, cyhy_db_name):
    """Return the S3 key of an org's plaintext ASM summary PDF.

    Matches the filename report_generator.py writes at
    ``Posture-and-Exposure-ASM-Summary_{org_code}_{end_date}.pdf`` (note the
    underscore separators, unlike the report filename above -- that's the
    existing report_generator.py convention, preserved here as-is).
    """
    return f"{report_date}/Posture-and-Exposure-ASM-Summary_{cyhy_db_name}_{report_date}.pdf"


def encrypted_object_key(report_date, filename):
    """Return the S3 key an encrypted copy of filename should be stored at.

    filename keeps the same basename as the plaintext report/ASM summary it
    was encrypted from, so it lands at
    ``<report_date>/<ENCRYPTED_PREFIX>/<filename>`` -- next to, not inside,
    the plaintext originals for that same report_date.
    """
    return f"{report_date}/{ENCRYPTED_PREFIX}/{filename}"


def object_exists(s3_client, bucket, key):
    """Return whether an S3 object exists, without downloading it.

    Parameters
    ----------
    s3_client : boto3.client
        A boto3 S3 client.

    bucket : str
        The S3 bucket to check.

    key : str
        The object key to check.

    Returns
    -------
    bool: True if the object exists, False if it does not.

    Throws
    ------
    ClientError: If head_object fails for any reason other than the object
    not existing (e.g. missing permissions).

    """
    # Third-Party Libraries
    from botocore.exceptions import ClientError

    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
            return False
        raise


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


def upload_encrypted_reports(s3_client, bucket, report_date, local_paths):
    """Upload password-encrypted PDFs to S3 under <report_date>/ENCRYPTED_PREFIX/.

    Parameters
    ----------
    s3_client : boto3.client
        A boto3 S3 client.

    bucket : str
        The S3 bucket to upload the encrypted PDFs to.

    report_date : str
        The report's date ("YYYY-MM-DD"), used as the destination date
        prefix -- the same one the plaintext originals were read from.

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
        key = encrypted_object_key(report_date, filename)
        s3_client.upload_file(local_path, bucket, key)
        LOGGER.debug("Uploaded %s to s3://%s/%s", local_path, bucket, key)
        uploaded_keys.append(key)

    return uploaded_keys
