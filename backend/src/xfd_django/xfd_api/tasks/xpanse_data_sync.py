"""Push Xpanse data from LZ to DMZ."""
# Standard Python Libraries
import json
import logging
import os

# Third-Party Libraries
from django.db.models import Prefetch
from django.forms.models import model_to_dict
import requests
from xfd_api.utils.chunk import chunk_list_by_bytes
from xfd_api.utils.csv_utils import create_checksum
from xfd_mini_dl.models import (
    XpanseAlerts,
    XpanseBusinessUnits,
    XpanseCveServiceMdl,
    XpanseServicesMdl,
)

LOGGER = logging.getLogger(__name__)


def handler(event):
    """Run main scan function."""
    try:
        is_dmz = os.getenv("IS_DMZ", "0") == "1"
        is_local = os.getenv("IS_LOCAL", "1") == "1"
        if not is_dmz and not is_local:
            LOGGER.warning("Scan can only be run in the DMZ or locally. Exitting now.")
            return {
                "statusCode": 200,
                "body": "DMZ Shodan Vulnerabilities and Asset cannot run outside the DMZ.",
            }
        LOGGER.info("Running Xpanse data sync to DMZ")
        main()
        return {
            "statusCode": 200,
            "body": "DMZ Shodan Vulnerabilities and Asset sync completed successfully.",
        }
    except Exception as e:
        LOGGER.error("Error in Xpanse data sync: %s", str(e))
        return {"statusCode": 500, "body": str(e)}


def chunk_and_post_data(business_units_list):
    """Chunk and post data to DMZ."""
    LOGGER.info("Chunking data into 2MB chunks")
    serialized_and_shaped_data = chunk_list_by_bytes(business_units_list, 2097152)
    LOGGER.info(
        "Serialized and shaped data into %d chunks", len(serialized_and_shaped_data)
    )
    for chunk in serialized_and_shaped_data:
        bounds = chunk["bounds"]
        data = json.dumps(chunk["chunk"], indent=4, default=str)
        with open(f"{bounds['start']}-{bounds['end']}.json", "w") as f:
            f.write(data)
        payload = {"data": data}
        checksum = create_checksum(data)
        headers = {
            "x-checksum": checksum,
            "x-cursor": f"{bounds['start']}-{bounds['end']}",
            "Content-Type": "application/json",
            "Authorization": os.getenv("DMZ_API_KEY"),
        }
        ENDPOINT_URL = f"{os.getenv('DMZ_SYNC_ENDPOINT')}/xpanse-sync"
        try:
            response = requests.post(
                ENDPOINT_URL, json=payload, headers=headers, timeout=60
            )
            if response.status_code == 200:
                LOGGER.info("Succesfully synced data to DMZ")
            else:
                LOGGER.error(
                    "Failed to sync data to DMZ: %d - %s",
                    response.status_code,
                    response.text,
                )
        except Exception as e:
            LOGGER.exception("Error syncing data to DMZ: %s", str(e))
            raise


def main():
    """Execute XpanseDataSync scan."""
    LOGGER.info("Starting Xpanse data sync to DMZ")
    business_units = XpanseBusinessUnits.objects.prefetch_related(
        Prefetch(
            "alerts",
            queryset=XpanseAlerts.objects.prefetch_related(
                Prefetch(
                    "services",
                    queryset=XpanseServicesMdl.objects.prefetch_related(
                        "sub_domains",
                        Prefetch(
                            "xpansecveservicemdl_set",
                            queryset=XpanseCveServiceMdl.objects.select_related(
                                "xpanse_inferred_cve"
                            ),
                        ),
                    ),
                )
            ),
        )
    ).distinct()

    business_units_list = []
    LOGGER.info("Shaping %d Records for Xpanse data sync", len(business_units))
    for business_unit in business_units:
        # business_unit = model_to_dict(business_unit)
        alerts = [model_to_dict(alert) for alert in business_unit.alerts.all()]
        for alert in alerts:
            services_list = []
            services = alert.get("services", [])
            for service in services:
                sub_domains_list = []
                cves_list = []
                service_dict = model_to_dict(service)
                sub_domains = service_dict.get("sub_domains", [])
                for sub_domain in sub_domains:
                    sub_domains_list.append(model_to_dict(sub_domain))
                # cves = service_dict.get("cves", [])
                for link in service.xpansecveservicemdl_set.all():
                    cve = link.xpanse_inferred_cve
                    if cve:
                        temp = model_to_dict(cve)
                        temp["product"] = link.product
                        temp["confidence"] = link.confidence
                        temp["vendor"] = link.vendor
                        temp["version_number"] = link.version_number
                        temp["activity_status"] = link.activity_status
                        temp["first_observed"] = link.first_observed
                        temp["last_observed"] = link.last_observed
                        cves_list.append(temp)
                # for cve in cves:
                #     cves_list.append(model_to_dict(cve))
                service_dict["cves"] = cves_list
                service_dict["sub_domains"] = sub_domains_list
                services_list.append(service_dict)
            alert["services"] = services_list
            del alert["business_units"]
        business_unit_dict = model_to_dict(business_unit)
        business_unit_dict["alerts"] = alerts
        business_units_list.append(business_unit_dict)
    chunk_and_post_data(business_units_list)


if __name__ == "__main__":
    main()
