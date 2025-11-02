"""Run bastion (Read-Only)."""
# Standard Python Libraries
import csv
from datetime import datetime
import io
import os

# Third-Party Libraries
import boto3
import django
from django.db import connection, connections
import psycopg2
import psycopg2.extras

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Third-Party Libraries
# Override database credentials for Lambda usage (read-only)
from django.conf import settings

# For the default database
readonly_user = os.environ.get("READ_ONLY_DB_USER")
readonly_pass = os.environ.get("READ_ONLY_DB_PASSWORD")
if readonly_user and readonly_pass:
    settings.DATABASES["default"]["USER"] = readonly_user
    settings.DATABASES["default"]["PASSWORD"] = readonly_pass
    settings.DATABASES["mini_data_lake"]["USER"] = readonly_user
    settings.DATABASES["mini_data_lake"]["PASSWORD"] = readonly_pass

# Close any existing connections so that new ones will use the updated credentials
connections.close_all()


def handler(event, context):
    """
    Execute database queries on different targets based on mode.

    Supports three modes: "db" (default database), "mdl" (mini_data_lake), and "redshift".
    If toCsv is true in the event, the query results will be saved as a CSV in an S3 bucket.
    """
    mode = event.get("mode")
    query = event.get("query")
    to_csv = event.get("toCsv", False)

    if not mode or not query:
        return {"status_code": 400, "body": "Mode and query are required in the event."}

    try:
        if mode == "db":
            return handle_db_query(query, to_csv)
        elif mode == "mdl":
            return handle_mdl_query(query, to_csv)
        elif mode == "redshift":
            return handle_redshift_query(query, to_csv)
        else:
            return {"status_code": 400, "body": f"Unsupported mode: {mode}"}
    except Exception as e:
        return {"status_code": 500, "body": f"Error: {str(e)}"}


def handle_db_query(query, to_csv):
    """Execute query on the default database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            # Extract column names from the cursor description
            columns = [desc[0] for desc in cursor.description]
        if to_csv:
            csv_url = generate_and_upload_csv(result, columns, "db")
            return {"status_code": 200, "body": f"CSV file uploaded to S3: {csv_url}"}
        return {"status_code": 200, "body": str(result)}
    except Exception as e:
        return {"status_code": 500, "body": f"Database error: {str(e)}"}


def handle_mdl_query(query, to_csv):
    """Execute query on the mini_data_lake database."""
    try:
        with connections["mini_data_lake"].cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
        if to_csv:
            csv_url = generate_and_upload_csv(result, columns, "mdl")
            return {"status_code": 200, "body": f"CSV file uploaded to S3: {csv_url}"}
        return {"status_code": 200, "body": str(result)}
    except Exception as e:
        return {"status_code": 500, "body": f"Mini Data Lake database error: {str(e)}"}


def handle_redshift_query(query, to_csv):
    """Execute query on the Redshift database."""
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get("REDSHIFT_DATABASE"),
            user=os.environ.get("REDSHIFT_USER"),
            password=os.environ.get("REDSHIFT_PASSWORD"),
            host=os.environ.get("REDSHIFT_HOST"),
            port=5439,
        )
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(query)
            results = cursor.fetchall()
            # For redshift, results are list of dictionaries. Extract columns if any rows are returned.
            columns = list(results[0].keys()) if results else []
        finally:
            cursor.close()
            conn.close()
        if to_csv:
            csv_url = generate_and_upload_csv(results, columns, "redshift")
            return {"status_code": 200, "body": f"CSV file uploaded to S3: {csv_url}"}
        return {"status_code": 200, "body": str(results)}
    except Exception as e:
        return {"status_code": 500, "body": f"Redshift error: {str(e)}"}


def generate_and_upload_csv(data, columns, mode):
    """Generate a CSV file from data and upload it to S3."""
    # Create an in-memory CSV file
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(columns)

    # Write data rows; if rows are dictionaries, extract values in order of the header
    if data:
        if isinstance(data[0], dict):
            for row in data:
                writer.writerow([row.get(col, "") for col in columns])
        else:
            for row in data:
                writer.writerow(row)

    csv_content = output.getvalue()
    output.close()

    # Generate a unique filename based on mode and current UTC timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{mode}_query_{timestamp}.csv"

    # Retrieve S3 bucket name from environment variables
    s3_bucket = os.environ.get("EXPORT_BUCKET_NAME")
    if not s3_bucket:
        raise Exception("S3_BUCKET environment variable not set.")

    s3_client = boto3.client("s3")
    s3_client.put_object(Bucket=s3_bucket, Key=filename, Body=csv_content)

    # Construct and return the S3 file URL (adjust the URL format if your bucket is public/private)
    s3_url = f"s3://{s3_bucket}/{filename}"
    return s3_url
