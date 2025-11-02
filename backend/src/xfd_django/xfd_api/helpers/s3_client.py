"""S3 Client."""
# Standard Python Libraries
from datetime import datetime
import logging
import os
import random

# Third-Party Libraries
import boto3

# Configure logging
LOGGER = logging.getLogger(__name__)

# Third-Party Libraries
from botocore.exceptions import ClientError


class S3Client:
    """S3 client."""

    def __init__(self, is_local=None):
        """Initialize."""
        self.is_local = (
            is_local
            if is_local is not None
            else bool(os.getenv("IS_OFFLINE") or os.getenv("IS_LOCAL"))
        )

        if self.is_local:
            self.s3 = boto3.client(
                "s3",
                endpoint_url="http://minio:9000",
                config=boto3.session.Config(s3={"addressing_style": "path"}),
            )
        else:
            self.s3 = boto3.client(
                "s3",
                config=boto3.session.Config(
                    s3={"addressing_style": "virtual"},
                    retries={"max_attempts": 3},
                    signature_version="s3v4",
                ),
            )

    def get_xpanse_business_units(self):
        """Retrieve CSV File from S3. Returns the file contents (as bytes)."""
        bucket_name = os.getenv("XPANSE_ORG_SYNC_BUCKET_NAME")
        response = self.s3.list_objects_v2(Bucket=bucket_name)
        contents = response.get("Contents", [])
        most_recent = max(contents, key=lambda obj: obj["LastModified"])
        key = most_recent["Key"]
        obj = self.s3.get_object(Bucket=bucket_name, Key=key)
        file_contents = obj["Body"].read().decode("utf-8")  # This will be bytes
        return file_contents

    def save_csv(self, body, name=""):
        """Save a CSV file in S3 and returns a temporary URL for access."""
        try:
            key = (
                name
                if name != ""
                else "{}/{}-{}.csv".format(
                    random.random(), name, datetime.utcnow().isoformat()
                )
            )
            bucket = os.getenv("EXPORT_BUCKET_NAME")

            # Save CSV to S3
            self.s3.put_object(
                Bucket=bucket, Key=key, Body=body, ContentType="text/csv"
            )

            # Generate signed URL
            url = self.get_presigned_url(bucket_name=bucket, object_key=key)
            return url
        except ClientError as e:
            LOGGER.exception("Error saving CSV to S3: %s", e)
            raise

    def export_report(self, report_name, org_id):
        """Generate a presigned URL for a report."""
        try:
            key = "{}/{}".format(org_id, report_name)
            bucket = os.getenv("REPORTS_BUCKET_NAME")

            # Generate signed URL
            url = self.get_presigned_url(bucket_name=bucket, object_key=key)
            return url
        except ClientError as e:
            LOGGER.exception("Error exporting report from S3: %s", e)
            raise

    def list_reports(self, org_id):
        """List all reports in a specified organization's folder."""
        try:
            bucket = os.getenv("REPORTS_BUCKET_NAME")
            prefix = "{}/".format(org_id)

            response = self.s3.list_objects_v2(
                Bucket=bucket, Prefix=prefix, Delimiter=""
            )
            return response.get("Contents", [])
        except ClientError as e:
            LOGGER.exception("Error listing reports from S3: %s", e)
            raise

    def pull_daily_vs(self, filename):
        """Retrieve a specified daily VS file from S3."""
        bucket = os.getenv("VS_BUCKET_NAME", "vs-extracts")

        try:
            response = self.s3.head_object(Bucket=bucket, Key=filename)
            if response:
                LOGGER.info("File '%s' exists in bucket %s.", filename, bucket)
        except self.s3.exceptions.NoSuchKey:
            LOGGER.info("File '%s' does not exist in bucket %s.", filename, bucket)
            return None
        except ClientError as e:
            LOGGER.exception("Error checking for file in S3: %s", e)
            raise

        try:
            response = self.s3.get_object(Bucket=bucket, Key=filename)
            return response["Body"].read() if "Body" in response else None
        except ClientError as e:
            LOGGER.exception("Error downloading file from S3: %s", e)
            raise

    def get_email_asset(self, file_name):
        """Retrieve an email template asset from S3."""
        bucket = os.getenv("EMAIL_BUCKET_NAME")

        try:
            response = self.s3.get_object(Bucket=bucket, Key=file_name)
            return (
                response["Body"].read().decode("utf-8") if "Body" in response else None
            )
        except ClientError as e:
            LOGGER.exception("Error retrieving email asset from S3: %s", e)
            raise

    def get_presigned_url(self, bucket_name, object_key, expiration=60 * 5):
        """Get Presigned URL from s3.

        Args:
            bucket_name (_str_): S3 bucket name
            object_key (_str_): S3 object key
            expiration (_int): URL expiration in seconds

        Returns:
            _str_: S3 presigned url string
        """
        url = self.s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expiration,
        )
        if self.is_local:
            url = url.replace("minio:9000", "localhost:9000")

        return url
