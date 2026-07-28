"""Unit tests for PE API database query and persistence functions."""

# Standard Python Libraries
from datetime import datetime
import os
import unittest
from unittest.mock import MagicMock, patch
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pe_reports_django.settings")
os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
# First-Party Libraries
from dataAPI import schemas, views
from django.core.exceptions import ObjectDoesNotExist

# Preserve the real Django model exception classes before patching the
# model names in dataAPI.views with MagicMock objects.
DOMAIN_PERMUTATIONS_DOES_NOT_EXIST = views.DomainPermutations.DoesNotExist
DOMAIN_ALERTS_DOES_NOT_EXIST = views.DomainAlerts.DoesNotExist


def call_without_transaction(function, *args, **kwargs):
    """Call a transaction-decorated view without opening a real DB connection."""
    undecorated_function = getattr(function, "__wrapped__", function)
    return undecorated_function(*args, **kwargs)


class OrganizationQueryTests(unittest.TestCase):
    """Verify organization and related lookup queries."""

    @patch("dataAPI.views.Organizations")
    def test_organizations_query_serializes_uuid_and_dates(self, organizations_mock):
        """Serialize database values returned by the organization query."""
        org_uid = uuid.uuid4()
        organizations_mock.objects.filter.return_value.values.return_value = [
            {
                "organizations_uid": org_uid,
                "org_type_uid": None,
                "parent_org_uid": None,
                "cyhy_period_start": datetime(2026, 1, 1),
                "date_first_reported": datetime(2026, 2, 1),
            }
        ]

        result = views.organizations_demo_or_report_on(tokens="test-key")

        self.assertEqual(result[0]["organizations_uid"], str(org_uid))
        self.assertEqual(result[0]["cyhy_period_start"], "2026-01-01")
        self.assertEqual(result[0]["date_first_reported"], "2026-02-01")
        organizations_mock.objects.filter.assert_called_once()

    @patch("dataAPI.views.DataSource")
    @patch("dataAPI.views.dt")
    def test_data_source_lookup_updates_last_run(self, dt_mock, data_source_mock):
        """Refresh last_run after reading a data-source row."""
        source_uid = uuid.uuid4()
        dt_mock.today.return_value = datetime(2026, 3, 4)
        first_query = MagicMock()
        first_query.values.return_value = [
            {
                "data_source_uid": source_uid,
                "name": "dnstwist",
                "description": "Domain permutations",
                "last_run": datetime(2026, 3, 1),
            }
        ]
        second_query = MagicMock()
        data_source_mock.objects.filter.side_effect = [first_query, second_query]

        result = views.data_source_by_name(
            schemas.DataSourceByNameInput(name="dnstwist"), tokens="test-key"
        )

        self.assertEqual(result[0]["data_source_uid"], str(source_uid))
        second_query.update.assert_called_once_with(last_run="2026-03-04")

    @patch("dataAPI.views.RootDomains")
    def test_root_domain_lookup_filters_on_org_and_enumeration(self, roots_mock):
        """Return only enumerated root domains belonging to the requested org."""
        root_uid = uuid.uuid4()
        roots_mock.objects.filter.return_value.values.return_value = [
            {
                "root_domain_uid": root_uid,
                "organizations_uid_id": uuid.uuid4(),
                "data_source_uid_id": uuid.uuid4(),
                "root_domain": "example.gov",
            }
        ]

        result = views.rootdomains_by_org_uid(
            schemas.RootdomainsByOrgUIDInput(org_uid="org-uid"), tokens="test-key"
        )

        roots_mock.objects.filter.assert_called_once_with(
            organizations_uid="org-uid", enumerate_subs=True
        )
        self.assertEqual(result[0]["root_domain_uid"], str(root_uid))


class SubdomainPersistenceTests(unittest.TestCase):
    """Verify subdomain insert and update query branches."""

    @patch("dataAPI.views.uuid.uuid4", side_effect=["root-uid", "subdomain-uid"])
    @patch("dataAPI.views.dt")
    @patch("dataAPI.views.SubDomains")
    @patch("dataAPI.views.RootDomains")
    @patch("dataAPI.views.DataSource")
    @patch("dataAPI.views.Organizations")
    def test_subdomain_insert_creates_missing_root_and_subdomain(
        self,
        organizations_mock,
        data_source_mock,
        roots_mock,
        subdomains_mock,
        dt_mock,
        _uuid_mock,
    ):
        """Create both related rows when neither root nor subdomain exists."""
        dt_mock.today.return_value = datetime(2026, 4, 5)
        organizations_mock.objects.filter.return_value.values.return_value = [
            {"cyhy_db_name": "DHS"}
        ]
        org_instance = MagicMock()
        organizations_mock.objects.get.return_value = org_instance
        source_instance = MagicMock()
        data_source_mock.objects.get.return_value = source_instance
        subdomains_mock.objects.filter.return_value.exists.return_value = False
        roots_mock.objects.filter.return_value.exists.return_value = False
        root_instance = MagicMock()
        roots_mock.objects.get.return_value = root_instance

        result = call_without_transaction(
            views.sub_domains_single_insert,
            schemas.SubDomainsSingleInsertInput(
                domain="example.gov", pe_org_uid="org-uid", root=True
            ),
            tokens="test-key",
        )

        roots_mock.objects.create.assert_called_once_with(
            root_domain_uid="root-uid",
            organizations_uid=org_instance,
            root_domain="example.gov",
            data_source_uid=source_instance,
            enumerate_subs=False,
        )
        subdomains_mock.objects.create.assert_called_once_with(
            sub_domain_uid="subdomain-uid",
            sub_domain="example.gov",
            root_domain_uid=root_instance,
            data_source_uid=source_instance,
            first_seen="2026-04-05",
            last_seen="2026-04-05",
            identified=False,
        )
        self.assertEqual(
            result,
            "1 records created, 0 records updated in the sub_domains table for DHS",
        )

    @patch("dataAPI.views.dt")
    @patch("dataAPI.views.SubDomains")
    @patch("dataAPI.views.Organizations")
    def test_existing_subdomain_updates_last_seen(
        self, organizations_mock, subdomains_mock, dt_mock
    ):
        """Update an existing organization-scoped subdomain instead of duplicating it."""
        dt_mock.today.return_value = datetime(2026, 4, 5)
        organizations_mock.objects.filter.return_value.values.return_value = [
            {"cyhy_db_name": "DHS"}
        ]
        query = MagicMock()
        query.exists.return_value = True
        subdomains_mock.objects.filter.return_value = query

        result = call_without_transaction(
            views.sub_domains_single_insert,
            schemas.SubDomainsSingleInsertInput(
                domain="www.example.gov", pe_org_uid="org-uid", root=False
            ),
            tokens="test-key",
        )

        query.update.assert_called_once_with(last_seen="2026-04-05", identified=False)
        self.assertEqual(
            result,
            "0 records created, 1 records updated in the sub_domains table for DHS",
        )


class DNSMonitorPersistenceTests(unittest.TestCase):
    """Verify DNSMonitor query create, update, skip, and duplicate branches."""

    @patch("dataAPI.views.DomainPermutations")
    @patch("dataAPI.views.SubDomains")
    @patch("dataAPI.views.DataSource")
    @patch("dataAPI.views.Organizations")
    def test_domain_permutation_creates_missing_record(
        self, organizations_mock, source_mock, subdomain_mock, permutations_mock
    ):
        """Create a permutation after resolving its foreign-key instances."""
        org_instance = MagicMock()
        source_instance = MagicMock()
        subdomain_instance = MagicMock()
        organizations_mock.objects.get.return_value = org_instance
        source_mock.objects.get.return_value = source_instance
        subdomain_mock.objects.get.return_value = subdomain_instance
        permutations_mock.DoesNotExist = DOMAIN_PERMUTATIONS_DOES_NOT_EXIST
        permutations_mock.objects.get.side_effect = DOMAIN_PERMUTATIONS_DOES_NOT_EXIST
        data = schemas.DomainPermuInsertInput(
            insert_data=[
                schemas.DomainPermuInsert(
                    organizations_uid="org-uid",
                    sub_domain_uid="sub-uid",
                    data_source_uid="source-uid",
                    domain_permutation="examp1e.gov",
                    ipv4="192.0.2.1",
                    date_observed="2026-05-01",
                )
            ]
        )

        result = call_without_transaction(
            views.domain_permu_insert, data, tokens="test-key"
        )

        permutations_mock.objects.create.assert_called_once()
        self.assertIn("1 created, 0 updated", result)

    @patch("dataAPI.views.DomainPermutations")
    @patch("dataAPI.views.SubDomains")
    @patch("dataAPI.views.DataSource")
    @patch("dataAPI.views.Organizations")
    def test_domain_permutation_updates_existing_record(
        self, organizations_mock, source_mock, subdomain_mock, permutations_mock
    ):
        """Update mutable values when an organization permutation already exists."""
        organizations_mock.objects.get.return_value = MagicMock()
        source_mock.objects.get.return_value = MagicMock()
        subdomain_mock.objects.get.return_value = MagicMock()
        query = MagicMock()
        permutations_mock.objects.filter.return_value = query
        data = schemas.DomainPermuInsertInput(
            insert_data=[
                schemas.DomainPermuInsert(
                    organizations_uid="org-uid",
                    sub_domain_uid="sub-uid",
                    data_source_uid="source-uid",
                    domain_permutation="examp1e.gov",
                    ipv4="192.0.2.2",
                    date_observed="2026-05-02",
                )
            ]
        )

        result = call_without_transaction(
            views.domain_permu_insert, data, tokens="test-key"
        )

        query.update.assert_called_once()
        self.assertIn("0 created, 1 updated", result)

    @patch("dataAPI.views.DomainPermutations")
    @patch("dataAPI.views.Organizations")
    def test_domain_permutation_skips_missing_related_records(
        self, organizations_mock, permutations_mock
    ):
        """Skip an input row when its organization or related rows do not exist."""
        organizations_mock.objects.get.side_effect = ObjectDoesNotExist("missing")
        data = schemas.DomainPermuInsertInput(
            insert_data=[
                schemas.DomainPermuInsert(
                    organizations_uid="missing",
                    domain_permutation="example.gov",
                )
            ]
        )

        result = call_without_transaction(
            views.domain_permu_insert, data, tokens="test-key"
        )

        permutations_mock.objects.create.assert_not_called()
        self.assertIn("0 created, 0 updated", result)

    @patch("dataAPI.views.uuid.uuid4", return_value="alert-uid")
    @patch("dataAPI.views.DomainAlerts")
    @patch("dataAPI.views.SubDomains")
    @patch("dataAPI.views.DataSource")
    @patch("dataAPI.views.Organizations")
    def test_domain_alert_creates_only_new_alert(
        self,
        organizations_mock,
        source_mock,
        subdomain_mock,
        alerts_mock,
        _uuid_mock,
    ):
        """Create an alert when the duplicate lookup has no match."""
        organizations_mock.objects.get.return_value = MagicMock()
        source_mock.objects.get.return_value = MagicMock()
        subdomain_mock.objects.get.return_value = MagicMock()
        alerts_mock.DoesNotExist = DOMAIN_ALERTS_DOES_NOT_EXIST
        alerts_mock.objects.get.side_effect = DOMAIN_ALERTS_DOES_NOT_EXIST
        data = schemas.DomainAlertsInsertInput(
            insert_data=[
                schemas.DomainAlertsInsert(
                    organizations_uid="org-uid",
                    sub_domain_uid="sub-uid",
                    data_source_uid="source-uid",
                    alert_type="ipv4_changed",
                    message="Address changed",
                    previous_value="192.0.2.1",
                    new_value="192.0.2.2",
                    date="2026-05-02",
                )
            ]
        )

        result = call_without_transaction(
            views.domain_alerts_insert, data, tokens="test-key"
        )

        alerts_mock.objects.create.assert_called_once()
        self.assertIn("1 created", result)

    @patch("dataAPI.views.DomainAlerts")
    @patch("dataAPI.views.SubDomains")
    @patch("dataAPI.views.DataSource")
    @patch("dataAPI.views.Organizations")
    def test_domain_alert_does_not_duplicate_existing_alert(
        self, organizations_mock, source_mock, subdomain_mock, alerts_mock
    ):
        """Do not insert a second alert matching the duplicate key."""
        organizations_mock.objects.get.return_value = MagicMock()
        source_mock.objects.get.return_value = MagicMock()
        subdomain_mock.objects.get.return_value = MagicMock()
        alerts_mock.objects.get.return_value = MagicMock()
        data = schemas.DomainAlertsInsertInput(
            insert_data=[
                schemas.DomainAlertsInsert(
                    organizations_uid="org-uid",
                    sub_domain_uid="sub-uid",
                    data_source_uid="source-uid",
                    alert_type="ipv4_changed",
                    new_value="192.0.2.2",
                    date="2026-05-02",
                )
            ]
        )

        result = call_without_transaction(
            views.domain_alerts_insert, data, tokens="test-key"
        )

        alerts_mock.objects.create.assert_not_called()
        self.assertIn("0 created", result)


if __name__ == "__main__":
    unittest.main()
