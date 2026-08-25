"""Tests for the remote ASM Sync orchestration step."""

# Standard Python Libraries
from contextlib import ExitStack
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, call, patch

PE_SOURCE_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PE_SOURCE_PATH))
os.environ.setdefault("PE_DB_NAME", "test_pe")
os.environ.setdefault("PE_DB_USERNAME", "test_user")
os.environ.setdefault("PE_DB_PASSWORD", "_".join(("test", "value")))

# Third-Party Libraries
import pandas as pd

with (
    patch("logging.basicConfig"),
    patch("logging.handlers.RotatingFileHandler"),
):
    # Third-Party Libraries
    from pe_asm.remote_step import asm_sync_remote, asm_sync_remote_query
    from pe_asm.remote_step.asm_sync_remote_helpers import (
        enum_ips_from_subs,
        enum_subs_from_ips,
        enum_subs_from_roots,
        shodan_dedupe,
        upsert_cyhy_cidrs,
    )


class RunAsmSyncRemoteTests(unittest.TestCase):
    """Verify organization selection and the per-organization sync workflow."""

    def setUp(self):
        """Create organizations representing report, demo, and explicit selections."""
        self.organizations = [
            {
                "organizations_uid": "uid-c",
                "cyhy_db_name": "C_ORG",
                "name": "C Organization",
                "agency_type": "Federal",
                "report_on": True,
                "demo": False,
            },
            {
                "organizations_uid": "uid-b",
                "cyhy_db_name": "B_DEMO",
                "name": "B Demo Organization",
                "agency_type": "Demo",
                "report_on": False,
                "demo": True,
            },
            {
                "organizations_uid": "uid-a",
                "cyhy_db_name": "A_ORG",
                "name": "A Organization",
                "agency_type": "Federal",
                "report_on": True,
                "demo": False,
            },
        ]
        self.workflow_names = [
            "upsert_cyhy_cidrs",
            "update_cidrs_status",
            "enum_subs_from_roots",
            "enum_subs_from_ips",
            "enum_ips_from_subs",
            "update_ips_status",
            "update_subs_status",
            "update_ips_subs_status",
            "update_subs_identified",
            "shodan_dedupe",
        ]

    def run_with_mocks(self, orgs_argument):
        """Run the remote workflow with database and enumeration calls mocked."""
        with ExitStack() as stack:
            get_orgs_mock = stack.enter_context(
                patch.object(
                    asm_sync_remote,
                    "get_orgs",
                    return_value=self.organizations,
                )
            )
            workflow_mocks = {
                name: stack.enter_context(patch.object(asm_sync_remote, name))
                for name in self.workflow_names
            }
            stack.enter_context(
                patch.object(asm_sync_remote.time, "time", return_value=100.0)
            )

            result = asm_sync_remote.run_asm_sync_remote(orgs_argument)

        get_orgs_mock.assert_called_once_with()
        self.assertIsNone(result)
        return workflow_mocks

    @staticmethod
    def dataframe_org_names(mock_function):
        """Return organization names passed in one-row dataframe arguments."""
        return [
            invocation.args[0].iloc[0]["cyhy_db_name"]
            for invocation in mock_function.call_args_list
        ]

    def assert_dataframe_workflow_orgs(self, workflow_mocks, expected_names):
        """Verify dataframe-based workflow helpers received selected orgs in order."""
        dataframe_helpers = [
            "upsert_cyhy_cidrs",
            "enum_subs_from_roots",
            "enum_subs_from_ips",
            "enum_ips_from_subs",
            "shodan_dedupe",
        ]
        for helper_name in dataframe_helpers:
            with self.subTest(helper=helper_name):
                self.assertEqual(
                    self.dataframe_org_names(workflow_mocks[helper_name]),
                    expected_names,
                )

    def assert_uid_workflow_calls(self, workflow_mocks, expected_uids):
        """Verify status helpers received one organization UID list per org."""
        uid_helpers = [
            "update_cidrs_status",
            "update_ips_status",
            "update_subs_status",
            "update_ips_subs_status",
            "update_subs_identified",
        ]
        expected_calls = [
            call([organization_uid]) for organization_uid in expected_uids
        ]
        for helper_name in uid_helpers:
            with self.subTest(helper=helper_name):
                self.assertEqual(
                    workflow_mocks[helper_name].call_args_list,
                    expected_calls,
                )

    def test_all_selects_reportable_organizations_in_sorted_order(self):
        """Process only report_on organizations and sort them by CyHy name."""
        workflow_mocks = self.run_with_mocks("all")

        self.assert_dataframe_workflow_orgs(
            workflow_mocks,
            ["A_ORG", "C_ORG"],
        )
        self.assert_uid_workflow_calls(
            workflow_mocks,
            ["uid-a", "uid-c"],
        )

    def test_demo_selects_only_demo_organizations(self):
        """Process organizations marked as demos for the DEMO shortcut."""
        workflow_mocks = self.run_with_mocks("DEMO")

        self.assert_dataframe_workflow_orgs(workflow_mocks, ["B_DEMO"])
        self.assert_uid_workflow_calls(workflow_mocks, ["uid-b"])

    def test_explicit_org_list_filters_and_sorts_requested_orgs(self):
        """Process only comma-separated organization names requested by the caller."""
        workflow_mocks = self.run_with_mocks("C_ORG,A_ORG")

        self.assert_dataframe_workflow_orgs(
            workflow_mocks,
            ["A_ORG", "C_ORG"],
        )
        self.assert_uid_workflow_calls(
            workflow_mocks,
            ["uid-a", "uid-c"],
        )

    def test_each_dataframe_contains_only_required_columns(self):
        """Pass a stable four-column organization dataframe to enumeration helpers."""
        workflow_mocks = self.run_with_mocks("A_ORG")

        dataframe = workflow_mocks["upsert_cyhy_cidrs"].call_args.args[0]
        pd.testing.assert_frame_equal(
            dataframe.reset_index(drop=True),
            pd.DataFrame(
                [
                    {
                        "organizations_uid": "uid-a",
                        "cyhy_db_name": "A_ORG",
                        "name": "A Organization",
                        "agency_type": "Federal",
                    }
                ]
            ),
        )


class EnumIpsFromSubsTests(unittest.TestCase):
    """Verify forward DNS results are linked to subdomains."""

    @patch.object(enum_ips_from_subs.socket, "gethostbyname", return_value="192.0.2.1")
    def test_get_ip_for_domain_returns_resolved_address(self, resolver_mock):
        """Return the IPv4 address supplied by the system resolver."""
        self.assertEqual(
            enum_ips_from_subs.get_ip_for_domain("www.example.gov"),
            "192.0.2.1",
        )
        resolver_mock.assert_called_once_with("www.example.gov")

    @patch.object(enum_ips_from_subs.socket, "gethostbyname", side_effect=OSError)
    def test_get_ip_for_domain_returns_none_on_resolution_error(self, _resolver_mock):
        """Treat DNS resolution failures as missing addresses."""
        self.assertIsNone(enum_ips_from_subs.get_ip_for_domain("missing.example.gov"))

    @patch.object(enum_ips_from_subs, "get_ip_for_domain", return_value="192.0.2.1")
    def test_link_ip_from_domain_calls_database_procedure(self, _resolver_mock):
        """Hash and link a resolved IP using the database procedure."""
        connection = MagicMock()
        cursor = connection.cursor.return_value

        result = enum_ips_from_subs.link_ip_from_domain(
            "www.example.gov",
            "root-uid",
            "org-uid",
            "unknown",
            connection,
        )

        expected_hash = enum_ips_from_subs.hashlib.sha256(b"192.0.2.1").hexdigest()
        self.assertEqual(result, 1)
        cursor.callproc.assert_called_once_with(
            "link_ips_and_subs",
            (
                enum_ips_from_subs.DATE,
                expected_hash,
                "192.0.2.1",
                "org-uid",
                "www.example.gov",
                "unknown",
                "root-uid",
                None,
            ),
        )
        cursor.fetchone.assert_called_once_with()
        connection.commit.assert_called_once_with()
        cursor.close.assert_called_once_with()

    @patch.object(enum_ips_from_subs, "get_ip_for_domain", return_value=None)
    def test_link_ip_from_domain_skips_unresolved_domain(self, _resolver_mock):
        """Do not open a cursor when a domain has no address."""
        connection = MagicMock()

        self.assertEqual(
            enum_ips_from_subs.link_ip_from_domain(
                "missing.example.gov",
                "root-uid",
                "org-uid",
                "unknown",
                connection,
            ),
            0,
        )
        connection.cursor.assert_not_called()

    @patch.object(enum_ips_from_subs, "link_ip_from_domain")
    @patch.object(enum_ips_from_subs, "query_subs_by_org")
    @patch.object(enum_ips_from_subs, "connect")
    def test_enum_ips_skips_null_subdomain_and_closes_connection(
        self,
        connect_mock,
        query_mock,
        link_mock,
    ):
        """Link real subdomains while skipping the Null_Sub sentinel."""
        connection = connect_mock.return_value
        query_mock.return_value = pd.DataFrame(
            [
                {"sub_domain": "Null_Sub", "root_domain_uid": "root-1"},
                {"sub_domain": "www.example.gov", "root_domain_uid": "root-2"},
            ]
        )
        organizations = pd.DataFrame(
            [{"organizations_uid": "org-uid", "cyhy_db_name": "EXAMPLE"}]
        )

        enum_ips_from_subs.enum_ips_from_subs(organizations)

        query_mock.assert_called_once_with("org-uid")
        link_mock.assert_called_once_with(
            "www.example.gov",
            "root-2",
            "org-uid",
            "unknown",
            connection,
        )
        connection.close.assert_called_once_with()


class EnumSubsFromIpsTests(unittest.TestCase):
    """Verify reverse DNS enumeration and IP chunk processing."""

    @patch.object(enum_subs_from_ips, "upsert_ips")
    @patch.object(enum_subs_from_ips.requests, "request")
    def test_reverse_lookup_returns_domains_and_upserts_ip(
        self,
        request_mock,
        upsert_mock,
    ):
        """Normalize WhoisXML domain results and ignore malformed entries."""
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "size": 3,
            "result": [
                {"name": "www.example.gov"},
                {"name": "mail.example.gov"},
                {"missing": "name"},
            ],
        }
        request_mock.return_value = response
        ip_object = {"ip": "192.0.2.1", "ip_hash": "hash"}

        domains, failures = enum_subs_from_ips.reverseLookup(
            ip_object,
            [],
            "Thread 1",
        )

        self.assertEqual(
            domains,
            [
                {"sub_domain": "www.example.gov", "root": "example.gov"},
                {"sub_domain": "mail.example.gov", "root": "example.gov"},
            ],
        )
        self.assertEqual(failures, [])
        upsert_mock.assert_called_once_with(ip_object)

    @patch.object(enum_subs_from_ips.time, "sleep")
    @patch.object(enum_subs_from_ips.requests, "request")
    def test_reverse_lookup_records_ip_after_max_retries(
        self,
        request_mock,
        sleep_mock,
    ):
        """Record an address when every WhoisXML request fails."""
        response = MagicMock(status_code=503)
        response.json.return_value = {"size": 0, "result": []}
        request_mock.return_value = response

        domains, failures = enum_subs_from_ips.reverseLookup(
            {"ip": "192.0.2.2"},
            [],
            "Thread 2",
        )

        self.assertEqual(domains, [])
        self.assertEqual(failures, ["192.0.2.2"])
        self.assertEqual(request_mock.call_count, 6)
        self.assertEqual(sleep_mock.call_count, 5)

    @patch.object(enum_subs_from_ips, "reverseLookup")
    def test_link_domain_from_ip_links_each_found_domain(self, reverse_mock):
        """Call the link procedure for every reverse-lookup domain."""
        reverse_mock.return_value = (
            [
                {"sub_domain": "one.example.gov", "root": "example.gov"},
                {"sub_domain": "two.example.gov", "root": "example.gov"},
            ],
            [],
        )
        connection = MagicMock()
        cursor = connection.cursor.return_value
        ip_object = {"ip": "192.0.2.1", "ip_hash": "hash"}

        domains = enum_subs_from_ips.link_domain_from_ip(
            ip_object,
            "org-uid",
            "WhoisXML",
            [],
            connection,
            "Thread 1",
        )

        self.assertEqual(len(domains), 2)
        self.assertEqual(cursor.callproc.call_count, 2)
        self.assertEqual(connection.commit.call_count, 2)
        self.assertEqual(cursor.close.call_count, 2)

    @patch.object(enum_subs_from_ips, "link_domain_from_ip")
    @patch.object(enum_subs_from_ips, "connect")
    def test_run_ip_chunk_processes_rows_and_closes_connection(
        self,
        connect_mock,
        link_mock,
    ):
        """Pass every IP row to the linking helper using one connection."""
        connection = connect_mock.return_value
        ips = pd.DataFrame(
            [
                {"ip": "192.0.2.1", "ip_hash": "hash-1"},
                {"ip": "192.0.2.2", "ip_hash": "hash-2"},
            ]
        )

        enum_subs_from_ips.run_ip_chunk("ORG", "org-uid", ips, "Thread 1")

        self.assertEqual(link_mock.call_count, 2)
        for invocation in link_mock.call_args_list:
            self.assertEqual(invocation.args[1:3], ("org-uid", "WhoisXML"))
            self.assertIs(invocation.args[4], connection)
        connection.close.assert_called_once_with()

    @patch.object(enum_subs_from_ips.threading, "Thread")
    @patch.object(enum_subs_from_ips, "query_cidrs_by_org")
    def test_enum_subs_builds_ip_rows_and_runs_five_threads(
        self,
        query_mock,
        thread_mock,
    ):
        """Expand CIDR hosts, split them into five dataframes, and join all threads."""
        query_mock.return_value = pd.DataFrame(
            [{"network": "192.0.2.0/30", "cidr_uid": "cidr-uid"}]
        )
        threads = [MagicMock() for _ in range(5)]
        thread_mock.side_effect = threads
        organizations = pd.DataFrame(
            [{"organizations_uid": "org-uid", "cyhy_db_name": "ORG"}]
        )

        enum_subs_from_ips.enum_subs_from_ips(organizations)

        query_mock.assert_called_once_with("org-uid")
        self.assertEqual(thread_mock.call_count, 5)
        chunk_lengths = [
            len(item.kwargs["args"][2]) for item in thread_mock.call_args_list
        ]
        self.assertEqual(sum(chunk_lengths), 2)
        for thread in threads:
            thread.start.assert_called_once_with()
            thread.join.assert_called_once_with()


class EnumSubsFromRootsTests(unittest.TestCase):
    """Verify WhoisXML root-domain enumeration and insertion."""

    @patch.object(
        enum_subs_from_roots, "get_data_source_uid", return_value="source-uid"
    )
    @patch.object(enum_subs_from_roots.requests, "request")
    def test_whoisxml_enumeration_includes_root_and_excludes_www(
        self,
        request_mock,
        _source_mock,
    ):
        """Return the root and discovered non-www subdomains with shared metadata."""
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "domainsList": ["www.example.gov", "mail.example.gov"]
        }
        request_mock.return_value = response

        with patch.dict(os.environ, {"WHOIS_XML_KEY": "test-key"}, clear=False):
            domains = enum_subs_from_roots.whoisxml_enum_subs_from_root(
                "example.gov",
                "root-uid",
            )

        self.assertEqual(
            [domain["sub_domain"] for domain in domains],
            ["example.gov", "mail.example.gov"],
        )
        self.assertTrue(
            all(domain["root_domain_uid"] == "root-uid" for domain in domains)
        )
        self.assertTrue(
            all(domain["data_source_uid"] == "source-uid" for domain in domains)
        )

    @patch.object(enum_subs_from_roots, "insert_sub_domains")
    @patch.object(enum_subs_from_roots, "whoisxml_enum_subs_from_root")
    @patch.object(enum_subs_from_roots, "query_roots")
    def test_enum_subs_queries_roots_and_inserts_each_result(
        self,
        query_mock,
        enumerate_mock,
        insert_mock,
    ):
        """Enumerate every queried root and insert its result dataframe."""
        query_mock.return_value = pd.DataFrame(
            [
                {"root_domain": "one.gov", "root_domain_uid": "root-1"},
                {"root_domain": "two.gov", "root_domain_uid": "root-2"},
            ]
        )
        enumerate_mock.side_effect = [
            [{"sub_domain": "one.gov"}],
            [{"sub_domain": "two.gov"}],
        ]
        organizations = pd.DataFrame([{"organizations_uid": "org-uid"}])

        enum_subs_from_roots.enum_subs_from_roots(organizations)

        query_mock.assert_called_once_with(["org-uid"])
        self.assertEqual(
            enumerate_mock.call_args_list,
            [call("one.gov", "root-1"), call("two.gov", "root-2")],
        )
        self.assertEqual(insert_mock.call_count, 2)
        self.assertEqual(
            insert_mock.call_args_list[0].args[0].loc[0, "sub_domain"],
            "one.gov",
        )


class ShodanDedupeTests(unittest.TestCase):
    """Verify Shodan filtering, deduplication, and orchestration."""

    def test_state_check_returns_matching_state_name(self):
        """Return a state name embedded in a Shodan organization string."""
        self.assertEqual(
            shodan_dedupe.state_check("State of Virginia Network"),
            "Virginia",
        )
        self.assertFalse(shodan_dedupe.state_check("Example Corporation"))
        self.assertFalse(shodan_dedupe.state_check(None))

    def test_search_filters_us_federal_results(self):
        """Exclude state-associated results for federal organizations."""
        api = MagicMock()
        api.search.return_value = {
            "total": 2,
            "matches": [
                {"org": "State of Virginia", "ip_str": "192.0.2.1"},
                {"org": "Example Corporation", "ip_str": "192.0.2.2"},
            ],
        }
        ip_objects = []

        total = shodan_dedupe.search(
            api,
            "net:192.0.2.0/24",
            ip_objects,
            "cidr-uid",
            "FEDERAL",
        )

        self.assertEqual(total, 2)
        self.assertEqual([item["ip"] for item in ip_objects], ["192.0.2.2"])
        self.assertEqual(ip_objects[0]["origin_cidr"], "cidr-uid")

    @patch.object(shodan_dedupe, "update_shodan_ips")
    @patch.object(shodan_dedupe, "search")
    def test_cidr_dedupe_deduplicates_discovered_ips(self, search_mock, update_mock):
        """Consolidate duplicate IP results before updating the database."""

        def add_result(_api, _query, ip_objects, cidr_uid, _org_type):
            ip_objects.append(
                {
                    "ip_hash": "hash",
                    "ip": "192.0.2.1",
                    "origin_cidr": cidr_uid,
                    "current": True,
                }
            )
            return 1

        search_mock.side_effect = add_result
        cidrs = pd.DataFrame(
            [
                {"network": "192.0.2.0/24", "cidr_uid": "cidr-1"},
                {"network": "192.0.2.0/25", "cidr_uid": "cidr-2"},
            ]
        )
        connection = MagicMock()

        shodan_dedupe.cidr_dedupe(cidrs, MagicMock(), "STATE", connection)

        dataframe = update_mock.call_args.args[1]
        self.assertEqual(len(dataframe), 1)
        self.assertEqual(dataframe.iloc[0]["ip"], "192.0.2.1")

    @patch.object(shodan_dedupe, "update_shodan_ips")
    def test_ip_dedupe_filters_federal_state_results(self, update_mock):
        """Only persist floating Shodan IPs allowed by agency-state filtering."""
        api = MagicMock()
        api.host.return_value = [
            {"org": "State of Virginia", "ip_str": "192.0.2.1"},
            {"org": "Example Corporation", "ip_str": "192.0.2.2"},
        ]
        connection = MagicMock()

        shodan_dedupe.ip_dedupe(
            api,
            ["192.0.2.1", "192.0.2.2"],
            "FEDERAL",
            connection,
        )

        dataframe = update_mock.call_args.args[1]
        self.assertEqual(dataframe["ip"].tolist(), ["192.0.2.2"])

    @patch.object(shodan_dedupe, "ip_dedupe")
    @patch.object(shodan_dedupe, "cidr_dedupe")
    @patch.object(shodan_dedupe, "query_floating_ips")
    @patch.object(shodan_dedupe, "query_cidrs_by_org")
    @patch.object(shodan_dedupe, "connect")
    @patch.object(shodan_dedupe, "shodan_api_init")
    def test_shodan_dedupe_runs_cidr_and_floating_ip_workflows(
        self,
        api_init_mock,
        connect_mock,
        cidr_query_mock,
        ip_query_mock,
        cidr_dedupe_mock,
        ip_dedupe_mock,
    ):
        """Query and process both Shodan asset sources for each organization."""
        api = MagicMock()
        api_init_mock.return_value = [api]
        connection = connect_mock.return_value
        cidrs = pd.DataFrame([{"network": "192.0.2.0/24"}])
        floating_ips = ["192.0.2.1"]
        cidr_query_mock.return_value = cidrs
        ip_query_mock.return_value = floating_ips
        organizations = pd.DataFrame(
            [
                {
                    "organizations_uid": "org-uid",
                    "cyhy_db_name": "ORG",
                    "agency_type": "FEDERAL",
                }
            ]
        )

        shodan_dedupe.shodan_dedupe(organizations)

        cidr_dedupe_mock.assert_called_once_with(cidrs, api, "FEDERAL", connection)
        ip_dedupe_mock.assert_called_once_with(
            api,
            floating_ips,
            "FEDERAL",
            connection,
        )
        connection.close.assert_called_once_with()


class UpsertCyhyCidrsTests(unittest.TestCase):
    """Verify CyHy CIDRs are passed to the insert procedure."""

    @patch.object(upsert_cyhy_cidrs, "query_cyhy_assets")
    @patch.object(upsert_cyhy_cidrs, "connect")
    def test_upserts_each_network_and_closes_connection(
        self,
        connect_mock,
        query_mock,
    ):
        """Commit each successful network upsert and close all resources."""
        connection = connect_mock.return_value
        cursor = connection.cursor.return_value
        query_mock.return_value = pd.DataFrame(
            [{"network": "192.0.2.0/24"}, {"network": "198.51.100.0/24"}]
        )
        organizations = pd.DataFrame(
            [{"organizations_uid": "org-uid", "cyhy_db_name": "ORG"}]
        )

        upsert_cyhy_cidrs.upsert_cyhy_cidrs(organizations)

        query_mock.assert_called_once_with("ORG")
        self.assertEqual(cursor.callproc.call_count, 2)
        self.assertEqual(
            [invocation.args[0] for invocation in cursor.callproc.call_args_list],
            ["insert_cidr", "insert_cidr"],
        )
        self.assertEqual(connection.commit.call_count, 2)
        self.assertEqual(cursor.close.call_count, 2)
        connection.close.assert_called_once_with()

    @patch.object(upsert_cyhy_cidrs, "query_cyhy_assets")
    @patch.object(upsert_cyhy_cidrs, "connect")
    def test_database_error_skips_commit_and_continues(
        self,
        connect_mock,
        query_mock,
    ):
        """Continue to later networks when a stored procedure call fails."""
        connection = connect_mock.return_value
        first_cursor = MagicMock()
        second_cursor = MagicMock()
        first_cursor.callproc.side_effect = RuntimeError("insert failed")
        connection.cursor.side_effect = [first_cursor, second_cursor]
        query_mock.return_value = pd.DataFrame(
            [{"network": "192.0.2.0/24"}, {"network": "198.51.100.0/24"}]
        )
        organizations = pd.DataFrame(
            [{"organizations_uid": "org-uid", "cyhy_db_name": "ORG"}]
        )

        upsert_cyhy_cidrs.upsert_cyhy_cidrs(organizations)

        self.assertEqual(connection.cursor.call_count, 2)
        connection.commit.assert_called_once_with()
        second_cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()


class PeDatabaseQueryTests(unittest.TestCase):
    """Verify PE queries build dataframes using a DBAPI cursor."""

    def test_query_pe_sectors_returns_cursor_rows_as_dataframe(self):
        """Return sector rows without passing the DBAPI connection to pandas."""
        connection = MagicMock(name="connection")
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.description = [
            ("sector_uid",),
            ("id",),
            ("acronym",),
            ("run_scorecards",),
        ]
        cursor.fetchall.return_value = [("sector-uid", "SECTOR", "SEC", True)]

        result = asm_sync_remote_query.query_pe_sectors(connection)

        self.assertEqual(
            result.to_dict("records"),
            [
                {
                    "sector_uid": "sector-uid",
                    "id": "SECTOR",
                    "acronym": "SEC",
                    "run_scorecards": True,
                }
            ],
        )
        cursor.execute.assert_called_once()
        cursor.fetchall.assert_called_once_with()

    def test_query_pe_orgs_returns_cursor_rows_as_dataframe(self):
        """Return organization rows with column names from cursor metadata."""
        connection = MagicMock(name="connection")
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.description = [
            ("organizations_uid",),
            ("cyhy_db_name",),
            ("name",),
            ("agency_type",),
            ("report_on",),
            ("fceb",),
            ("scorecard",),
        ]
        cursor.fetchall.return_value = [
            ("org-uid", "ORG", "Organization", "Federal", True, False, True)
        ]

        result = asm_sync_remote_query.query_pe_orgs(connection)

        self.assertEqual(
            result.to_dict("records"),
            [
                {
                    "organizations_uid": "org-uid",
                    "cyhy_db_name": "ORG",
                    "name": "Organization",
                    "agency_type": "Federal",
                    "report_on": True,
                    "fceb": False,
                    "scorecard": True,
                }
            ],
        )
        cursor.execute.assert_called_once()
        cursor.fetchall.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
