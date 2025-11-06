"""Task for syncronizing Pshtt scan results with the DMZ sync endpoint."""
# Standard Python Libraries
import hashlib
import json
import logging
import os

# Third-Party Libraries
from django.forms.models import model_to_dict
import requests
from xfd_api.utils.chunk import chunk_list_by_bytes
from xfd_mini_dl.models import PshttResults

LOGGER = logging.getLogger(__name__)
SALT = os.getenv("CHECKSUM_SALT", "default_salt")
SYNC_ENDPOINT = os.getenv("DMZ_SYNC_ENDPOINT")
IS_LOCAL = os.getenv("IS_LOCAL") == "1"


def handler(event):
    """Handle the Pshtt sync task."""
    try:
        LOGGER.info("Made it to the handler of pshtt_scan_sync.py")
        main(event)
    except Exception as e:
        LOGGER.info("Error in pshtt task: %s", e)


def main(event):
    """Ingest Pshtt scan results and post them to the sync endpoint."""
    LOGGER.info("Running Pshtt scan sync with event: %s", event)
    results = []
    try:
        results = PshttResults.objects.select_related(
            "sub_domain",
            "sub_domain__data_source",  # Follow relation from sub_domain to data_source
            "organization",
            "data_source",
            "sub_domain__root_domain",
            "sub_domain__dns_record",
        ).all()
    except Exception as e:
        LOGGER.error("Error fetching Pshtt results: %s", e)
        return
    shaped_results = []
    try:
        for result in results:
            result_dict = model_to_dict(result)
            result_dict["sub_domain"] = model_to_dict(result.sub_domain)
            result_dict["sub_domain"]["data_source"] = (
                model_to_dict(result.sub_domain.data_source)
                if result.sub_domain.data_source
                else None
            )
            result_dict["sub_domain"]["root_domain"] = (
                model_to_dict(result.sub_domain.root_domain)
                if result.sub_domain.root_domain
                else None
            )
            result_dict["sub_domain"]["dns_record"] = (
                model_to_dict(result.sub_domain.dns_record)
                if result.sub_domain.dns_record
                else None
            )
            result_dict["data_source"] = (
                model_to_dict(result.data_source) if result.data_source else None
            )
            result_dict["organization"] = model_to_dict(result.organization)
            # Serialize the dict - model_to_dict does not handle UUID or datetime conversion
            shaped_results.append(result_dict)
    except Exception as e:
        LOGGER.error("Error shaping and traversing Pshtt results: %s", e)
        return

    try:
        chunked_results = chunk_list_by_bytes(shaped_results, 100_000)
    except Exception as e:
        LOGGER.error("Error chunking serialized pshtt result records: %s", e)
        return

    for chunk in chunked_results:
        # Compute checksum for the chunk
        # Post the chunk to the pshtt_sync endpoint
        data = json.dumps(chunk["chunk"], default=str)
        calculated_checksum = hashlib.sha256((SALT + data).encode()).hexdigest()
        try:
            # endpoint = SYNC_ENDPOINT + "/pshtt_sync"
            endpoint = (
                (SYNC_ENDPOINT + "/pshtt_sync")
                if IS_LOCAL
                else "http://backend:3000/pshtt_sync"
            )
            serialized_data = json.dumps({"data": chunk["chunk"]}, default=str)
            LOGGER.info("Serialized data for chunk: %s", serialized_data)
            response = requests.post(
                endpoint,
                data=serialized_data,
                headers={
                    "X-Checksum": calculated_checksum,
                    "X-API-KEY": os.getenv("DMZ_API_KEY"),
                    "Content-Type": "application/json",
                },
                timeout=60,
            )
            LOGGER.info("Posted chunk to pshtt_sync endpoint: %s", response.status_code)
        except Exception as e:
            LOGGER.error("Error posting chunk to pshtt_sync endpoint: %s", e)
            continue
