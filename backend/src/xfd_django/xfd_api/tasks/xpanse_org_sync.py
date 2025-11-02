"""XpanseOrgSync scan."""
# Standard Python Libraries
import csv
import io
import logging
import os
import re

# Third-Party Libraries
import django
from xfd_api.helpers.s3_client import S3Client
from xfd_mini_dl.models import Organization, XpanseBusinessUnits

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
django.setup()

# Third-Party Libraries
# cisagov Libraries

LOGGER = logging.getLogger(__name__)


def extract_last_substring_in_square_brackets(input_string):
    """Extract the last substring within square brackets from a string."""
    pattern = r"\[([^\]]+)\]"  # Matches [ followed by any characters that are not ], followed by ]

    # Find all matches of the pattern in the input_string
    matches = re.findall(pattern, input_string)
    # Return the last match or None if no matches are found
    return matches[-1] if matches else None


def insert_or_update_business_unit(business_unit_dict):
    """Insert or update a business unit in the database."""
    entity_name = business_unit_dict["entity_name"]
    del business_unit_dict["entity_name"]
    try:
        _, created = XpanseBusinessUnits.objects.update_or_create(
            entity_name=entity_name, defaults=business_unit_dict
        )
        if created:
            LOGGER.info("Created %s", entity_name)
        else:
            LOGGER.info("Updated %s", entity_name)
    except Exception as e:
        LOGGER.error("Unknown error saving: %s", e)


def main(_event):
    """Sync orgs to the database."""
    s3_client = S3Client(is_local=True)
    xpanse_bu_csv = None
    try:
        xpanse_bu_csv = s3_client.get_xpanse_business_units()
    except Exception as e:
        LOGGER.error("Error retrieving CSV from S3: %s", e)
        return
    orgs_reader = csv.DictReader(io.StringIO(xpanse_bu_csv))
    for org in orgs_reader:
        try:
            cyhy_db_name = extract_last_substring_in_square_brackets(
                org["Entity Name"].strip()
            )
            org_record = None
            try:
                mdl_org_record = Organization.objects.filter(acronym=cyhy_db_name)
                if mdl_org_record.first():
                    org_record = mdl_org_record[0]
            except Organization.DoesNotExist:
                LOGGER.error("Organization not found: %s", cyhy_db_name)
            except Exception as e:
                LOGGER.error("Unknown error saving: %s", e)
            business_unit_dict = {
                "entity_name": org["Entity Name"].strip(),
                "state": org["State"].strip(),
                "county": org["County"].strip(),
                "city": org["City"].strip(),
                "sector": org["Sector"].strip(),
                "entity_type": org["Entity Type"].strip(),
                "region": org["Region"].strip(),
                "rating": int(org["Rating"].strip()),
                "cyhy_db_name": org_record,
            }
            insert_or_update_business_unit(business_unit_dict)
        except Exception as e:
            LOGGER.error("Failure saving %s", org["Entity Name"])
            LOGGER.error("Unknown error saving: %s", e)
            continue

    LOGGER.info("Finished Updating Xpanse Organizations")


def handler(event):
    """Xpanse Organizations sync handler."""
    try:
        is_dmz = os.getenv("IS_DMZ")
        is_local = os.getenv("IS_LOCAL")
        if str(is_dmz).lower() not in {"true", "1"} and not is_local:
            LOGGER.warning("Scan can only be run in the DMZ or locally. Exiting now.")
            return {
                "statusCode": 200,
                "body": "Xpanse Alerts sync cannot run outside the DMZ.",
            }
        main(event)
        return {
            "statusCode": 200,
            "body": "Xpanse Alerts sync completed successfully.",
        }
    except Exception as e:
        LOGGER.error("Error in handler: %s", e)
        return {"statusCode": 500, "body": str(e)}


# if __name__ == "__main__":
#     main()
