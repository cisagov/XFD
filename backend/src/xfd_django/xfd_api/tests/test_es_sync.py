"""Test Elasticsearch organization sync."""
# Standard Python Libraries
from datetime import datetime
from unittest.mock import patch

# Third-Party Libraries
import pytest
from xfd_api.tasks.helpers.syncdb_helpers.es_sync import sync_es_organizations
from xfd_mini_dl.models import Organization


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.helpers.syncdb_helpers.es_sync.es_client")
def test_sync_es_organizations_excludes_retired(mock_es_client):
    """Retired organizations should be deleted from ES and not re-indexed."""
    active_org = Organization.objects.create(
        name="Active ES Org",
        root_domains=["active.com"],
        ip_blocks=[],
        is_passive=False,
        retired=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    retired_org = Organization.objects.create(
        name="Retired ES Org",
        root_domains=["retired.com"],
        ip_blocks=[],
        is_passive=False,
        retired=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    sync_es_organizations()

    mock_es_client.delete_organizations.assert_called_once()
    deleted_ids = mock_es_client.delete_organizations.call_args[0][0]
    assert retired_org.id in deleted_ids

    mock_es_client.update_organizations.assert_called_once()
    synced_orgs = mock_es_client.update_organizations.call_args[0][0]
    synced_ids = {org["id"] for org in synced_orgs}
    assert active_org.id in synced_ids
    assert retired_org.id not in synced_ids
    assert all(org.get("retired") is False for org in synced_orgs)
