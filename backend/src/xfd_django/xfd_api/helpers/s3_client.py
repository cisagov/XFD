# Standard Python Libraries
import csv
from datetime import datetime
import os
from random import randint

# Third-Party Libraries
import boto3
import boto3.s3
from django.core.paginator import Paginator
from django.http import HttpResponse
from fastapi import HTTPException
from minio import Minio


def get_minio_client():
    return Minio(
        "localhost:9000",
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=False,
    )


async def save_minio(data, key: str):
    client = get_minio_client()
    try:
        if not client.bucket_exists(os.environ["EXPORT_BUCKET_NAME"]):
            client.make_bucket(os.environ["EXPORT_BUCKET_NAME"])

        client.put_object(os.environ["EXPORT_BUCKET_NAME"], data, key)
        print("File uploaded successfully")
    except Exception as e:
        print(f"Error uploading file to Minio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def export_to_csv(pages: Paginator, queryset, name, is_local: bool = True):
    try:
        filename = f"{randint(0, 1000000000)}/{name}-{datetime.now()}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={filename}"

        writer = csv.writer(response)
        if queryset.count() > 0:
            writer.writerow(
                [
                    "id",
                    "createdAt",
                    "updatedAt",
                    "syncedAt",
                    "ip",
                    "fromRootDomain",
                    "subdomainSource",
                    "ipOnly",
                    "reverseName",
                    "name",
                    "screenshot",
                    "country",
                    "asn",
                    "cloudHosted",
                    "ssl",
                    "censysCertificatesResults",
                    "trustymailResults",
                    "discoveredById_id",
                    "organizationId_id",
                ]
            )

        for page_number in pages.page_range:
            page = pages.page(page_number)
            for obj in page.object_list:
                print(obj)
                writer.writerow(
                    [
                        obj.id,
                        obj.createdAt,
                        obj.updatedAt,
                        obj.syncedAt,
                        obj.ip,
                        obj.fromRootDomain,
                        obj.subdomainSource,
                        obj.ipOnly,
                        obj.reverseName,
                        obj.name,
                        obj.screnshot,
                        obj.country,
                        obj.asn,
                        obj.cloudHosted,
                        obj.ssl,
                        obj.censysCertificatesResults,
                        obj.trustymailResults,
                        obj.discoveredById_id,
                        obj.organizationId_id,
                    ]
                )
            # if not is_local:
            #    s3_client = boto3.client("s3")
            #    s3_client.put_object(
            #        Body=response.content,
            #        Bucket=os.environ['EXPORT_BUCKET_NAME'],
            #        Key=filename
            #    )
            # else:
            #    client = get_minio_client()
            #    csv_values = response.getvalue()
            #    if not client.bucket_exists(os.environ['EXPORT_BUCKET_NAME']):
            #        client.make_bucket(os.environ['EXPORT_BUCKET_NAME'])
            #    client.put_object(
            #        os.environ['EXPORT_BUCKET_NAME'],
            #        filename,
            #        len(csv_values),
            #        content_type='text/csv'
            #         )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
