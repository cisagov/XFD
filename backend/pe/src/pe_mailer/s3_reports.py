"""Helpers for reading generated P&E report PDFs out of S3.

Fargate tasks have no shared/persistent local disk, so report PDFs
produced by the (not yet migrated) report-generation side are expected to
land in S3 rather than a local directory. The convention mirrors the old
local layout 1:1: objects are stored under a per-org prefix named for the
org's cyhy_db_name, e.g.:

    s3://<BUCKET>/<cyhy_db_name>/Posture_and_Exposure_Report-2026-07-30.pdf
    s3://<BUCKET>/<cyhy_db_name>/Posture-and-Exposure-ASM-Summary-2026-07-30.pdf
"""

# Standard Python Libraries
import logging
import os

LOGGER = logging.getLogger(__name__)


def list_org_report_keys(s3_client, bucket, cyhy_db_name):
    """Return the sorted list of *.pdf object keys under an org's S3 prefix.

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
    list(str): Sorted .pdf object keys found under the prefix.

    """
    prefix = f"{cyhy_db_name}/"
    keys = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].lower().endswith(".pdf"):
                keys.append(obj["Key"])

    return sorted(keys)


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
