"""Use DNS twist to fuzz domain names and cross check with a blacklist."""
# Standard Python Libraries
import datetime
import hashlib
import json
import logging
import os
from uuid import UUID

# Third-Party Libraries
from django.db.models import Count, Prefetch
from django.forms.models import model_to_dict
import requests
from xfd_api.utils.chunk import chunk_list_by_bytes
from xfd_mini_dl.models import DomainPermutations, Organization

DB_NAME = "mini_data_lake"
SALT = os.getenv("CHECKSUM_SALT", "default_salt")
IS_CONCURRENT = True

date = datetime.datetime.now().strftime("%Y-%m-%d")
LOGGER = logging.getLogger(__name__)


def make_json_serializable(data: dict) -> dict:
    """Convert UUID and datetime values in a dict to strings."""
    serializable = {}
    for key, value in data.items():
        if isinstance(value, UUID):
            serializable[key] = str(value)
        elif isinstance(value, datetime.datetime):
            serializable[key] = value.isoformat()
        else:
            serializable[key] = value
    return serializable


def main(event):
    """Run DNStwist on certain domains and upload findings to database."""
    organization_id = None
    if isinstance(event, dict):
        organization_id = event.get("organizationId")
    try:
        organizations = (
            Organization.objects.annotate(num_permutations=Count("domainpermutations"))
            .prefetch_related(
                Prefetch(
                    "domainpermutations_set", queryset=DomainPermutations.objects.all()
                )
            )
            .order_by("-num_permutations")
        )
        # Only pull data that relates to the organization id if provided (is only provided in concurrent mode)
        if IS_CONCURRENT and organization_id:
            # REVERT THIS WHEN READY
            organizations = organizations.filter(id=organization_id)
        shaped_orgs = []
        for org in organizations:
            domain_permutations = [
                model_to_dict(dp) for dp in org.domainpermutations_set.all()
            ]
            shaped_domain_permutations = []
            for dp in domain_permutations:
                shaped_domain_permutations.append(make_json_serializable(dp))
            org_dict = {
                "id": org.id,
                "name": org.name,
                "acronym": org.acronym,
                "domain_permutations": shaped_domain_permutations,
            }
            shaped_orgs.append(org_dict)
        chunked_list_by_bytes = chunk_list_by_bytes(shaped_orgs, 100_000)
        for chunk in chunked_list_by_bytes:
            if len(chunk["chunk"]) > 0:
                # Only proceed if there are domain permutations to send to the sync endpoint
                # domain_permutations = chunk["chunk"].get("domain_permutations", [])
                # if len(domain_permutations) == 0:
                #     continue

                data = chunk["chunk"]
                serialized = json.dumps(data, default=str, sort_keys=True)
                salted_checksum = hashlib.sha256(
                    (SALT + serialized).encode()
                ).hexdigest()
                # Send to endpoint
                headers = {
                    "X-Salted-Checksum": salted_checksum,
                    "Content-Type": "application/json",
                    "Authorization": os.getenv("DMZ_API_KEY", ""),
                }

                requests.post(
                    f"{os.getenv('DMZ_SYNC_ENDPOINT')}/dns_twist_sync",
                    headers=headers,
                    json=serialized,
                    timeout=60,
                )
                # response = requests.post("http://backend:3000/dns_twist_sync", headers=headers, json={"data": serialized})
                LOGGER.info(
                    "Sent %s domain permutations to sync endpoint",
                    len(domain_permutations),
                )
    except Exception as e:
        LOGGER.info("Error in main: %s", e)


def handler(event):
    """Dns Twist sync handler."""
    try:
        is_dmz = os.getenv("IS_DMZ", "0") == "1"
        # is_local = os.getenv("IS_LOCAL", "1") == "1"
        if is_dmz:
            LOGGER.warning("Scan can only be run in the Prod or locally. Exiting now.")
            return {
                "statusCode": 200,
                "body": "Xpanse Alerts sync cannot run outside Prod or local.",
            }
        main(event)
        return {
            "statusCode": 200,
            "body": "Xpanse Alerts sync completed successfully.",
        }
    except Exception as e:
        LOGGER.error("Error in handler: %s", e)
        return {"statusCode": 500, "body": str(e)}
