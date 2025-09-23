"""
Insert or update CVE records and retrieve associated product data.

Define functions to:
- Insert or update a CVE record in the database along with its related CPE information.
- Retrieve a CVE and group its associated products by vendor.

Log operations and handle exceptions to ensure smooth API interactions.
"""

# Standard Library Imports
# Standard Python Libraries
import datetime
import logging

# Third-Party Libraries
from django.forms.models import model_to_dict
from xfd_mini_dl.models import Cpe, Cve

# Third Party Imports


LOGGER = logging.getLogger(__name__)


def api_cve_insert(cve_dict):
    """
    Insert a cve record for  into the cve table with linked products and venders.

    On conflict, update the old record with the new data

    Args:
        cve_dict: Dictionary of column names and values to be inserted

    Return:
        Status on if the record was inserted successfully
    """
    try:
        # Get WAS record based on tag
        vender_prod_dict = cve_dict.get("vender_product", {})
        cve_object, created = Cve.objects.update_or_create(
            name=cve_dict.get("cve_name"),
            defaults={
                "published_at": cve_dict.get("published_date"),
                "modified_at": cve_dict.get("last_modified_date"),
                "status": cve_dict.get("vuln_status"),
                "description": cve_dict.get("description"),
                "cvss_v2_source": cve_dict.get("cvss_v2_source"),
                "cvss_v2_type": cve_dict.get("cvss_v2_type"),
                "cvss_v2_version": cve_dict.get("cvss_v2_version"),
                "cvss_v2_vector_string": cve_dict.get("cvss_v2_vector_string"),
                "cvss_v2_base_score": cve_dict.get("cvss_v2_base_score"),
                "cvss_v2_base_severity": cve_dict.get("cvss_v2_base_severity"),
                "cvss_v2_exploitability_score": cve_dict.get(
                    "cvss_v2_exploitability_score"
                ),
                "cvss_v2_impact_score": cve_dict.get("cvss_v2_impact_score"),
                "cvss_v3_source": cve_dict.get("cvss_v3_source"),
                "cvss_v3_type": cve_dict.get("cvss_v3_type"),
                "cvss_v3_version": cve_dict.get("cvss_v3_version"),
                "cvss_v3_vector_string": cve_dict.get("cvss_v3_vector_string"),
                "cvss_v3_base_score": cve_dict.get("cvss_v3_base_score"),
                "cvss_v3_base_severity": cve_dict.get("cvss_v3_base_severity"),
                "cvss_v3_exploitability_score": cve_dict.get(
                    "cvss_v3_exploitability_score"
                ),
                "cvss_v3_impact_score": cve_dict.get("cvss_v3_impact_score"),
                "cvss_v4_source": cve_dict.get("cvss_v4_source"),
                "cvss_v4_type": cve_dict.get("cvss_v4_type"),
                "cvss_v4_version": cve_dict.get("cvss_v4_version"),
                "cvss_v4_vector_string": cve_dict.get("cvss_v4_vector_string"),
                "cvss_v4_base_score": cve_dict.get("cvss_v4_base_score"),
                "cvss_v4_base_severity": cve_dict.get("cvss_v4_base_severity"),
                "cvss_v4_exploitability_score": cve_dict.get(
                    "cvss_v4_exploitability_score"
                ),
                "cvss_v4_impact_score": cve_dict.get("cvss_v4_impact_score"),
                "weaknesses": cve_dict.get("weaknesses"),
                "reference_urls": cve_dict.get("reference_urls"),
                "cpe_list": cve_dict.get("cpe_list"),
            },
        )
        if created:
            LOGGER.info("new CVE record created for %s", cve_dict.get("cve_name"))

        prod_obj_list = []
        for vendor, product_list in vender_prod_dict.items():
            for product, version in product_list:
                product_obj, product_created = Cpe.objects.update_or_create(
                    vendor=vendor,
                    name=product,
                    version=version,
                    defaults={
                        "last_seen_at": datetime.datetime.now(datetime.timezone.utc)
                    },
                )
                prod_obj_list.append(product_obj)

        cve_object.cpes.add(*prod_obj_list)
        cve_object.save()

        # TODO no ticket is needed for this todo, this code may be needed in the future
        # prods = []
        # for prod in list(cve_object.cpes.all()):
        #     prods.append(
        #         {
        #             "cpe_product_uid": prod.cpe_product_uid,
        #             "cpe_product_name": prod.cpe_product_name,
        #             "version_number": prod.version_number,
        #             "vender_uid": prod.cpe_vender_uid_id,
        #             "vender_name": prod.cpe_vender_uid.vender_name,
        #         }
        #     )
        # return {
        #     "message": "Record updated successfully.",
        #     "updated_cve": cve_object,
        #     "products": prods,
        # }

    except Exception as e:
        LOGGER.error("Error occurred: %s", e)
        LOGGER.info("API key expired please try again")


def get_cve_and_products(cve_name):
    """
    Query DB to retrieve a CVE and its associated products data for the specified CVE.

    Args:
        cve_name (str): The CVE name or code.

    Returns:
        dict: A dictionary containing:
              - "cve_data": A dict representation of the CVE record.
              - "products": A dictionary mapping each vendor to a list of related product info.
              If the CVE does not exist, returns {"message": "CVE does not exist"}.
    """
    LOGGER.info("Retrieving CVE with name: %s", cve_name)
    try:
        # Note: the new model uses the field 'name'
        cve = Cve.objects.get(name=cve_name)
        # Get all related Cpe records from the ManyToMany field 'cpes'
        products = cve.cpes.all()
        vend_prod_dict = {}
        for prod in products:
            vendor = prod.vendor  # 'vendor' is a CharField in the new Cpe model
            if vendor not in vend_prod_dict:
                vend_prod_dict[vendor] = []
            vend_prod_dict[vendor].append(
                {
                    "cpe_id": prod.id,
                    "name": prod.name,
                    "version": prod.version,
                    "vendor": prod.vendor,
                    "last_seen_at": prod.last_seen_at,
                }
            )
        cve_dict = model_to_dict(cve)
        return {"cve_data": cve_dict, "products": vend_prod_dict}
    except Cve.DoesNotExist:
        return {"message": "CVE does not exist"}
    except Exception as e:
        LOGGER.error("An error occurred: %s", e, exc_info=True)
        return {"message": "An error occurred"}
