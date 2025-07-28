"""ES client."""
# Standard Python Libraries
import logging
import os

# Third-Party Libraries
from elasticsearch import Elasticsearch, helpers

# Constants
DOMAINS_INDEX = "domains-5"
ORGANIZATIONS_INDEX = "organizations-1"

# Define mappings
organization_mapping = {
    "properties": {"name": {"type": "text"}, "suggest": {"type": "completion"}}
}

domain_mapping = {
    "properties": {
        "services": {"type": "nested"},
        "vulnerabilities": {"type": "nested"},
        "webpage_body": {"type": "text", "term_vector": "yes"},
        "parent_join": {"type": "join", "relations": {"domain": "webpage"}},
        "suggest": {"type": "completion"},
    }
}

# Raise log level for Elasticsearch client to WARNING to suppress request logs
logging.getLogger("elasticsearch").setLevel(logging.WARNING)

# Also suppress low-level logs from urllib3 used by Elasticsearch
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)


class ESClient:
    """ES Client."""

    def __init__(self):
        """Initialize the Elasticsearch client."""
        endpoint = os.getenv("ELASTICSEARCH_ENDPOINT")
        self.client = Elasticsearch(endpoint)

    def sync_organizations_index(self):
        """Create or updates the organizations index with mappings."""
        try:
            if not self.client.indices.exists(index=ORGANIZATIONS_INDEX):
                logging.info("Creating index %s...", ORGANIZATIONS_INDEX)
                self.client.indices.create(
                    index=ORGANIZATIONS_INDEX,
                    body={
                        "mappings": organization_mapping,
                        "settings": {"number_of_shards": 2},
                    },
                )
            else:
                logging.info("Updating index %s...", ORGANIZATIONS_INDEX)
                self.client.indices.put_mapping(
                    index=ORGANIZATIONS_INDEX, body=organization_mapping
                )
        except Exception as e:
            logging.error("Error syncing organizations index: %s", e)
            raise e

    def sync_domains_index(self):
        """Create or updates the domains index with mappings."""
        try:
            if not self.client.indices.exists(index=DOMAINS_INDEX):
                logging.info("Creating index %s...", DOMAINS_INDEX)
                self.client.indices.create(
                    index=DOMAINS_INDEX,
                    body={
                        "mappings": domain_mapping,
                        "settings": {"number_of_shards": 2},
                    },
                )
            else:
                logging.info("Updating index %s...", DOMAINS_INDEX)
                self.client.indices.put_mapping(
                    index=DOMAINS_INDEX, body=domain_mapping
                )
            # Set refresh interval
            self.client.indices.put_settings(
                index=DOMAINS_INDEX, body={"settings": {"refresh_interval": "1800s"}}
            )
        except Exception as e:
            logging.error("Error syncing domains index: %s", e)
            raise e

    def update_organizations(self, organizations):
        """Update or inserts organizations into Elasticsearch."""
        actions = [
            {
                "_op_type": "update",
                "_index": ORGANIZATIONS_INDEX,
                "_id": org["id"],
                "doc": {**org, "suggest": [{"input": org["name"], "weight": 1}]},
                "doc_as_upsert": True,
            }
            for org in organizations
        ]
        self._bulk_update(actions)

    def update_domains(self, domains):
        """Update or insert domains into Elasticsearch."""
        actions = [
            {
                "_op_type": "update",
                "_index": DOMAINS_INDEX,
                "_id": domain["id"],
                "doc": {
                    **domain,
                    "suggest": [{"input": domain["name"], "weight": 1}],
                    "parent_join": "domain",
                },
                "doc_as_upsert": True,
            }
            for domain in domains
        ]
        self._bulk_update(actions)

    def delete_all(self):
        """Delete all indices in Elasticsearch."""
        try:
            print("Deleting all indices...")
            self.client.indices.delete(index="*")
        except Exception as e:
            logging.error("Error deleting all indices: %s", e)
            raise e

    def search_domains(self, body):
        """Search domains index with specified query body."""
        return self.client.search(index=DOMAINS_INDEX, body=body)

    def search_organizations(self, body):
        """Search organizations index with specified query body."""
        return self.client.search(index=ORGANIZATIONS_INDEX, body=body)

    def _bulk_update(self, actions):
        """Update to Elasticsearch."""
        try:
            success_count, response = helpers.bulk(
                self.client, actions, raise_on_error=False
            )

            for idx, item in enumerate(response):
                if "update" in item and item["update"].get("error"):
                    logging.error(
                        "Error indexing document %s: %s", idx, item["update"]["error"]
                    )
                else:
                    logging.info("Successfully indexed document %s: %s", idx, item)

            self.client.indices.refresh(index="domains-5")
        except Exception as e:
            logging.error("Bulk operation error: %s", e)
            raise e
