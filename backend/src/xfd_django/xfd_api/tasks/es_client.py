"""ES client."""
# Standard Python Libraries
import logging
import os
import time

# Third-Party Libraries
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import TransportError

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
LOGGER = logging.getLogger(__name__)
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
                LOGGER.info("Creating index %s...", ORGANIZATIONS_INDEX)
                self.client.indices.create(
                    index=ORGANIZATIONS_INDEX,
                    body={
                        "mappings": organization_mapping,
                        "settings": {"number_of_shards": 2},
                    },
                )
            else:
                LOGGER.info("Updating index %s...", ORGANIZATIONS_INDEX)
                self.client.indices.put_mapping(
                    index=ORGANIZATIONS_INDEX, body=organization_mapping
                )
        except Exception as e:
            LOGGER.error("Error syncing organizations index: %s", e)
            raise e

    def sync_domains_index(self):
        """Create or updates the domains index with mappings."""
        try:
            if not self.client.indices.exists(index=DOMAINS_INDEX):
                LOGGER.info("Creating index %s...", DOMAINS_INDEX)
                self.client.indices.create(
                    index=DOMAINS_INDEX,
                    body={
                        "mappings": domain_mapping,
                        "settings": {"number_of_shards": 2},
                    },
                )
            else:
                LOGGER.info("Updating index %s...", DOMAINS_INDEX)
                self.client.indices.put_mapping(
                    index=DOMAINS_INDEX, body=domain_mapping
                )
            # Set refresh interval
            self.client.indices.put_settings(
                index=DOMAINS_INDEX, body={"settings": {"refresh_interval": "1800s"}}
            )
        except Exception as e:
            LOGGER.error("Error syncing domains index: %s", e)
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

    def update_domains(self, domains, max_retries=5, backoff_base=2):
        """Update or insert domains into Elasticsearch with retry and backoff."""
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

        attempt = 0
        while attempt <= max_retries:
            try:
                success, response = helpers.bulk(
                    self.client,
                    actions,
                    raise_on_error=False,
                    raise_on_exception=False,
                    request_timeout=60,
                )

                failed = [
                    item
                    for item in response
                    if "update" in item and item["update"].get("error")
                ]
                success_count = success
                failure_count = len(failed)

                logging.info(
                    f"Bulk sync: {success_count} succeeded, {failure_count} failed."
                )

                if failure_count:
                    for i, item in enumerate(failed):
                        logging.warning(
                            "Error on document %s: %s", i, item["update"]["error"]
                        )

                return  # Exit after success (even with partial failures)

            except TransportError as sync_error:
                if sync_error.status_code == 429:
                    wait_time = backoff_base**attempt
                    logging.warning(
                        "429 received, retrying in %s seconds...", wait_time
                    )
                    time.sleep(wait_time)
                    attempt += 1
                else:
                    logging.error("Unexpected error during bulk update: %s", sync_error)
                    raise sync_error

        raise Exception("Max retries exceeded for bulk update.")

    def delete_all(self):
        """Delete all indices in Elasticsearch."""
        try:
            LOGGER.info("Deleting all indices...")
            self.client.indices.delete(index="*")
        except Exception as e:
            LOGGER.error("Error deleting all indices: %s", e)
            raise e

    def search_domains(self, body, **kwargs):
        """Search domains index with specified query body."""
        return self.client.search(index=DOMAINS_INDEX, body=body, **kwargs)

    def scroll_domains(self, scroll_id: str, keepalive: str = "2m"):
        """Fetch the next batch of results for a scroll context."""
        return self.client.scroll(scroll_id=scroll_id, params={"scroll": keepalive})

    def clear_scroll_domains(self, scroll_id: str):
        """Clear the scroll context to free resources."""
        return self.client.clear_scroll(body={"scroll_id": [scroll_id]})

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
                    LOGGER.error(
                        "Error indexing document %s: %s", idx, item["update"]["error"]
                    )
                else:
                    LOGGER.info("Successfully indexed document %s: %s", idx, item)

            self.client.indices.refresh(index="domains-5")
        except Exception as e:
            LOGGER.error("Bulk operation error: %s", e)
            raise e
