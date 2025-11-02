"""Handler for syncing domain permutations from DNSTwist records from higher environments to the data lake."""
# Standart Python Libraries
# Standard Python Libraries
import datetime
import hashlib
import json
import logging
import os
from uuid import uuid4

# Third-Party Libraries
from fastapi import HTTPException
from requests import Request

# Project Imports
from xfd_api.auth import is_global_view_admin
from xfd_mini_dl.models import DataSource, DomainPermutations, Organization

LOGGER = logging.getLogger(__name__)
SALT = os.getenv("CHECKSUM_SALT", "default_salt")

DB_NAME = (
    "mini_data_lake_secondary" if os.getenv("IS_LOCAL", "") == "1" else "mini_data_lake"
)


async def dns_twist_sync_post(sync_body, request: Request, current_user):
    """Ingest and persist domain permutations to the data lake."""
    LOGGER.info("DB_NAME: %s", DB_NAME)
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")
    checksum = request.headers.get("x-salted-checksum")
    if not checksum:
        raise HTTPException(status_code=500, detail="No checksum error")
    if not sync_body.data:
        raise HTTPException(status_code=500, detail="Body invalid")
    calculated_checksum = create_checksum(sync_body.data)
    if checksum != calculated_checksum:
        raise HTTPException(status_code=500, detail="Checksum doesn't match error.")

    data_source, _ = DataSource.objects.using(DB_NAME).get_or_create(
        name="DNSTwist",
        description="DNSTwist is a domain name permutation engine.",
        last_run=datetime.datetime.now(),
    )
    orgs_with_dps = json.loads(sync_body.data)
    LOGGER.info("DATA: %s", orgs_with_dps)
    for org in orgs_with_dps:
        domain_permutations = org.get("domain_permutations", [])
        org_record = Organization.objects.using(DB_NAME).get(
            acronym=org.get("acronym", None)
        )
        LOGGER.info(
            "Got %d permutations for org %s",
            len(domain_permutations),
            org.get("name"),
        )
        for dp in domain_permutations:
            try:
                DomainPermutations.objects.using(DB_NAME).update_or_create(
                    domain_permutation=dp["domain_permutation"],
                    organization=org_record,
                    defaults={
                        "suspected_domain_uid": uuid4(),
                        "data_source": data_source,
                        "date_active": dp["date_active"],
                        "date_observed": dp["date_observed"],
                        "dshield_attack_count": dp["dshield_attack_count"],
                        "dshield_record_count": dp["dshield_record_count"],
                        "fuzzer": dp["fuzzer"],
                        "ipv4": dp["ipv4"],
                        "organization": org_record,
                        "ipv6": dp["ipv6"],
                        "malicious": dp["malicious"],
                        "name_server": dp["name_server"],
                        "ssdeep_score": dp["ssdeep_score"],
                        "blocklist_report_count": dp["blocklist_report_count"],
                        "blocklist_attack_count": dp["blocklist_attack_count"],
                    },
                )
            except Exception as e:
                LOGGER.error("Error saving domain permutation: %s", e)
    return {"status": "success"}


def create_checksum(data):
    """Validate the checksum from an API response."""
    try:
        # Recompute the checksum
        calculated_checksum = hashlib.sha256((SALT + data).encode()).hexdigest()

        return calculated_checksum
    except Exception as e:
        LOGGER.error("Error validating checksum: %s", e)
        return None
