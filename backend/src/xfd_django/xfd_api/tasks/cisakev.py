"""Collect current KEVs from cisa."""

# Standard Python Libraries
from datetime import datetime
import logging
import uuid

# Third-Party Libraries
from django.db.models import F
import requests
from xfd_mini_dl.models import CisaKevCatalog, Cve


def flag_known_exploited_cves():
    """Flag CVEs that match KEV entries by updating their descriptions."""
    kev_ids = set(CisaKevCatalog.objects.values_list("cve_id", flat=True))
    updated = Cve.objects.filter(name__in=kev_ids).update(
        description=F("description") + "\n\n⚠️ This CVE is on the CISA KEV list."
    )
    return updated


class CisaKevScan:
    """Class-based scanner for ingesting the CISA KEV catalog."""

    KEV_JSON_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

    def __init__(self):
        """Initialize the CISA KEV scan with a logger."""
        self.logger = logging.getLogger(__name__)

    def parse_date(self, date_str):
        """Convert a date string to a date object, or return None."""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            return None

    def parse_boolean(self, value):
        """Convert a value to boolean if possible."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "true"
        return False

    def run(self):
        """Pull KEV data and update the catalog."""
        try:
            self.logger.info("Requesting CISA KEV catalog...")
            response = requests.get(self.KEV_JSON_URL, timeout=10)
            response.raise_for_status()

            kev_data = response.json()
            vulnerabilities = kev_data.get("vulnerabilities", [])
            self.logger.info("Retrieved %d KEV entries.", len(vulnerabilities))

            # Step 1: Clear table
            CisaKevCatalog.objects.all().delete()
            self.logger.info("Cleared existing KEV catalog table.")

            # Step 2: Ingest new entries
            entries = [
                CisaKevCatalog(
                    cisa_kev_uid=uuid.uuid4(),
                    cve_id=entry.get("cveID"),
                    vendor_project=entry.get("vendorProject"),
                    product=entry.get("product"),
                    vulnerability_name=entry.get("vulnerabilityName"),
                    date_added=self.parse_date(entry.get("dateAdded")),
                    short_description=entry.get("shortDescription"),
                    required_action=entry.get("requiredAction"),
                    due_date=self.parse_date(entry.get("dueDate")),
                    notes=entry.get("notes"),
                    cwe_id=(entry.get("cwes") or [None])[0],
                    known_ransomware_campaign_use=self.parse_boolean(
                        entry.get("knownRansomwareCampaignUse")
                    ),
                    vulnerability_publish_date=self.parse_date(
                        entry.get("vulnerabilityPublishDate")
                    ),
                )
                for entry in vulnerabilities
            ]

            CisaKevCatalog.objects.bulk_create(entries)
            self.logger.info("Inserted %d records into CisaKevCatalog.", len(entries))

            # Step 3: Flag CVEs that are now on the KEV list
            flagged_count = flag_known_exploited_cves()
            self.logger.info(
                "Flagged %d CVE records as known exploited.", flagged_count
            )

        except Exception as e:
            self.logger.exception("Failed to ingest CISA KEV catalog: %s", e)


def handler(*args, **kwargs):
    """Run the main entry point for the scan."""
    return CisaKevScan().run()
