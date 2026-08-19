"""Tests for the local ASM Sync step."""

# Standard Python Libraries
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, call, patch

LOCAL_STEP_PATH = Path(__file__).resolve().parents[1] / "src" / "pe_asm" / "local_step"
sys.path.insert(0, str(LOCAL_STEP_PATH))

# Third-Party Libraries
with patch("os.makedirs"), patch("logging.basicConfig"):
    # Third-Party Libraries
    import asm_sync_local  # noqa: E402  pylint: disable=wrong-import-position
    import asm_sync_local_helpers  # noqa: E402  pylint: disable=wrong-import-position


class RunAsmSyncLocalTests(unittest.TestCase):
    """Verify local ASM Sync coordinates its external dependencies correctly."""

    def setUp(self):
        """Create representative CyHy results and database connections."""
        self.pe_connection = MagicMock(name="pe_connection")
        self.cyhy_connection = MagicMock(name="cyhy_connection")
        self.cyhy_results = [
            MagicMock(name="assets_df"),
            MagicMock(name="child_parent_dict"),
            MagicMock(name="contacts_df"),
            MagicMock(name="cyhy_agency_df"),
            MagicMock(name="sector_info_list"),
            MagicMock(name="sector_list"),
        ]
        self.input_values = [
            "/keys/pe.pem",
            "pe-key-password",
            "/keys/cyhy.pem",
            "cyhy-key-password",
        ]

    def run_with_mocks(self, local_db):
        """Run the orchestration function with every external boundary mocked."""
        with (
            patch("builtins.input", side_effect=self.input_values) as input_mock,
            patch.object(
                asm_sync_local,
                "get_ssm_parameter",
                side_effect=lambda parameter: "resolved:{}".format(parameter),
            ) as ssm_mock,
            patch.object(
                asm_sync_local,
                "local_db_connect",
                return_value=self.pe_connection,
            ) as local_connect_mock,
            patch.object(
                asm_sync_local,
                "pe_db_connect",
                return_value=self.pe_connection,
            ) as pe_connect_mock,
            patch.object(
                asm_sync_local,
                "cyhy_db_connect",
                return_value=self.cyhy_connection,
            ) as cyhy_connect_mock,
            patch.object(
                asm_sync_local,
                "retrieve_all_cyhy_data",
                return_value=self.cyhy_results,
            ) as retrieve_mock,
            patch.object(asm_sync_local, "insert_all_cyhy_data") as insert_mock,
            patch.object(
                asm_sync_local,
                "identify_org_asset_changes",
            ) as identify_mock,
            patch.object(asm_sync_local, "install_pgcrypto") as pgcrypto_mock,
            patch.object(
                asm_sync_local,
                "add_tables_uniq_constraint",
            ) as constraints_mock,
            patch.object(
                asm_sync_local,
                "add_tables_default_uid",
            ) as defaults_mock,
            patch.object(asm_sync_local.time, "sleep") as sleep_mock,
            patch.object(
                asm_sync_local.time,
                "time",
                return_value=100.0,
            ),
            patch.object(asm_sync_local.subprocess, "run") as subprocess_mock,
            patch.dict(os.environ, {}, clear=False),
        ):
            asm_sync_local.run_asm_sync_local(local_db=local_db)

            self.assertEqual(input_mock.call_count, 4)
            self.assertEqual(ssm_mock.call_count, 6)
            cyhy_connect_mock.assert_called_once_with()
            retrieve_mock.assert_called_once_with(self.cyhy_connection)
            insert_mock.assert_called_once_with(
                self.pe_connection,
                *self.cyhy_results,
            )
            identify_mock.assert_called_once_with(self.pe_connection)
            self.pe_connection.close.assert_called_once_with()
            subprocess_mock.assert_called_once_with(
                ["/usr/bin/killall", "SCREEN"],
                check=True,
                timeout=30,
            )

            self.assertEqual(os.environ["PE_DB_PKEY_LOCATION"], "/keys/pe.pem")
            self.assertEqual(os.environ["CYHY_DB_PKEY_LOCATION"], "/keys/cyhy.pem")
            self.assertEqual(os.environ["LOCAL_DB_DATABASE"], "pe")
            self.assertEqual(
                os.environ["WHOISXML_KEY"],
                "resolved:/crossfeed/staging/WHOIS_XML_KEY",
            )

            return {
                "constraints": constraints_mock,
                "defaults": defaults_mock,
                "local_connect": local_connect_mock,
                "pe_connect": pe_connect_mock,
                "pgcrypto": pgcrypto_mock,
                "sleep": sleep_mock,
            }

    def test_local_database_initializes_schema_before_sync(self):
        """Prepare local PostgreSQL before inserting retrieved CyHy data."""
        mocks = self.run_with_mocks(local_db=True)

        mocks["local_connect"].assert_called_once_with()
        mocks["pe_connect"].assert_not_called()
        mocks["pgcrypto"].assert_called_once_with(self.pe_connection)
        mocks["constraints"].assert_called_once_with(self.pe_connection)
        mocks["defaults"].assert_called_once_with(self.pe_connection)
        mocks["sleep"].assert_not_called()

    def test_remote_database_uses_tunnel_connection(self):
        """Use the PE database connection without local schema preparation."""
        mocks = self.run_with_mocks(local_db=False)

        mocks["pe_connect"].assert_called_once_with()
        mocks["local_connect"].assert_not_called()
        mocks["pgcrypto"].assert_not_called()
        mocks["constraints"].assert_not_called()
        mocks["defaults"].assert_not_called()
        self.assertEqual(mocks["sleep"].call_args_list, [call(5)])


class MainTests(unittest.TestCase):
    """Verify the command entry point selects the local database workflow."""

    @patch.object(asm_sync_local, "run_asm_sync_local")
    def test_main_uses_local_database(self, run_mock):
        """Run the local database branch from the command entry point."""
        asm_sync_local.main()

        run_mock.assert_called_once_with(True)


class GetSsmParameterTests(unittest.TestCase):
    """Verify encrypted SSM parameters are retrieved and errors propagate."""

    @patch.object(asm_sync_local_helpers.boto3, "client")
    def test_returns_decrypted_parameter_value(self, client_mock):
        """Request decryption and return the nested parameter value."""
        ssm_client = client_mock.return_value
        ssm_client.get_parameter.return_value = {"Parameter": {"Value": "secret-value"}}

        value = asm_sync_local_helpers.get_ssm_parameter("/crossfeed/test/key")

        self.assertEqual(value, "secret-value")
        client_mock.assert_called_once_with("ssm")
        ssm_client.get_parameter.assert_called_once_with(
            Name="/crossfeed/test/key",
            WithDecryption=True,
        )

    @patch.object(asm_sync_local_helpers.boto3, "client")
    def test_client_error_is_propagated(self, client_mock):
        """Do not hide failures returned by AWS Systems Manager."""
        error = asm_sync_local_helpers.ClientError(
            {"Error": {"Code": "ParameterNotFound", "Message": "missing"}},
            "GetParameter",
        )
        client_mock.return_value.get_parameter.side_effect = error

        with self.assertRaises(asm_sync_local_helpers.ClientError):
            asm_sync_local_helpers.get_ssm_parameter("/crossfeed/missing")


class CheckAccessorRunningTests(unittest.TestCase):
    """Verify accessor startup and connection command selection."""

    @patch.object(asm_sync_local_helpers.Path, "resolve")
    @patch.object(asm_sync_local_helpers.time, "sleep")
    @patch.object(asm_sync_local_helpers.subprocess, "run")
    def test_running_accessor_starts_connection_script(
        self,
        subprocess_mock,
        _sleep_mock,
        resolve_mock,
    ):
        """Connect to an accessor that EC2 reports as running."""
        status_result = MagicMock(stdout="line1\nline2\nline3\na b running\n")
        subprocess_mock.side_effect = [MagicMock(), status_result, MagicMock()]
        resolve_mock.return_value = Path("/resolved/startEC2Connect")

        with patch.dict(os.environ, {"PE_EC2_INST_ID": "i-123"}, clear=False):
            asm_sync_local_helpers.check_accessor_running()

        self.assertEqual(subprocess_mock.call_count, 3)
        self.assertEqual(
            subprocess_mock.call_args_list[2],
            call(
                ["/resolved/startEC2Connect"],
                check=True,
                timeout=30,
            ),
        )

    @patch.object(asm_sync_local_helpers.time, "sleep")
    @patch.object(asm_sync_local_helpers.subprocess, "run")
    def test_stopped_accessor_is_started_and_rechecked(
        self,
        subprocess_mock,
        sleep_mock,
    ):
        """Start a stopped accessor, wait, and recursively check its state."""
        status_result = MagicMock(stdout="line1\nline2\nline3\na b stopped\n")
        subprocess_mock.side_effect = [MagicMock(), status_result, MagicMock()]
        original_function = asm_sync_local_helpers.check_accessor_running

        with (
            patch.dict(os.environ, {"PE_EC2_INST_ID": "i-123"}, clear=False),
            patch.object(
                asm_sync_local_helpers,
                "check_accessor_running",
            ) as recursive_mock,
        ):
            original_function()

        recursive_mock.assert_called_once_with()
        self.assertIn(call(120), sleep_mock.call_args_list)
        self.assertIn("start-instances", subprocess_mock.call_args_list[2].args[0])


class DatabaseConnectionTests(unittest.TestCase):
    """Verify helper functions build database connections from environment values."""

    @patch.object(asm_sync_local_helpers.psycopg2, "connect")
    def test_local_database_connection_uses_environment(self, connect_mock):
        """Pass local PostgreSQL settings to psycopg2."""
        test_password = "-".join(("local", "test", "value"))
        environment = {
            "LOCAL_DB_HOST": "db",
            "LOCAL_DB_USER": "pe",
            "LOCAL_DB_PASSWORD": test_password,
            "LOCAL_DB_DATABASE": "pe",
            "LOCAL_DB_PORT": "5432",
        }
        with patch.dict(os.environ, environment, clear=False):
            connection = asm_sync_local_helpers.local_db_connect()

        self.assertIs(connection, connect_mock.return_value)
        connect_mock.assert_called_once_with(
            host="db",
            user="pe",
            password=test_password,
            dbname="pe",
            port="5432",
        )

    @patch.object(asm_sync_local_helpers.psycopg2, "connect")
    def test_local_database_operational_error_returns_none(self, connect_mock):
        """Return None when PostgreSQL cannot establish the local connection."""
        connect_mock.side_effect = asm_sync_local_helpers.OperationalError("offline")

        self.assertIsNone(asm_sync_local_helpers.local_db_connect())

    @patch.object(asm_sync_local_helpers.time, "sleep")
    @patch.object(asm_sync_local_helpers, "check_accessor_running")
    @patch.object(asm_sync_local_helpers, "SSHTunnelForwarder")
    @patch.object(asm_sync_local_helpers.psycopg2, "connect")
    def test_pe_database_connection_uses_ssh_tunnel(
        self,
        connect_mock,
        tunnel_mock,
        accessor_mock,
        _sleep_mock,
    ):
        """Connect PostgreSQL through the accessor's forwarded local port."""
        tunnel_mock.return_value.local_bind_port = 45678
        test_password = "-".join(("remote", "test", "value"))
        environment = {
            "PE_DB_PKEY_LOCATION": "/keys/pe.pem",
            "PE_DB_PKEY_PASS": "key-password",
            "PE_DB_HOST": "remote-db",
            "PE_DB_PORT": "5432",
            "PE_DB_USER": "pe",
            "PE_DB_PASSWORD": test_password,
            "PE_DB_DATABASE": "pe",
        }
        with patch.dict(os.environ, environment, clear=False):
            connection = asm_sync_local_helpers.pe_db_connect()

        self.assertIs(connection, connect_mock.return_value)
        accessor_mock.assert_called_once_with()
        tunnel_mock.return_value.start.assert_called_once_with()
        connect_mock.assert_called_once_with(
            host="localhost",
            user="pe",
            password=test_password,
            dbname="pe",
            port=45678,
        )

    @patch.object(asm_sync_local_helpers.Path, "resolve")
    @patch.object(asm_sync_local_helpers.time, "sleep")
    @patch.object(asm_sync_local_helpers.subprocess, "run")
    @patch.object(asm_sync_local_helpers, "MongoClient")
    def test_cyhy_database_connection_uses_mongodb_uri(
        self,
        mongo_mock,
        subprocess_mock,
        _sleep_mock,
        resolve_mock,
    ):
        """Start the CyHy tunnel and select the cyhy Mongo database."""
        resolve_mock.return_value = Path("/resolved/screenConnectCyHy")
        cyhy_database = MagicMock(name="cyhy_database")
        mongo_mock.return_value.__getitem__.return_value = cyhy_database
        environment = {
            "CYHY_DB_HOST": "localhost",
            "CYHY_DB_USER": "cyhy_ops",
            "CYHY_DB_PASSWORD": "password",
            "CYHY_DB_PORT": "27017",
            "CYHY_DB_DATABASE": "cyhy",
        }
        with patch.dict(os.environ, environment, clear=False):
            connection = asm_sync_local_helpers.cyhy_db_connect()

        self.assertIs(connection, cyhy_database)
        subprocess_mock.assert_called_once_with(
            ["/resolved/screenConnectCyHy"],
            check=True,
            timeout=30,
        )
        mongo_mock.assert_called_once_with(
            "mongodb://cyhy_ops:password@localhost:27017/cyhy"
        )


class DotgovDomainsTests(unittest.TestCase):
    """Verify the dot-gov domain CSV is downloaded and normalized."""

    @patch.object(asm_sync_local_helpers.requests, "get")
    def test_normalizes_dotgov_column_names(self, get_mock):
        """Return a dataframe using PE column names."""
        get_mock.return_value.content = (
            b"Domain name,Domain type,Organization name,Suborganization name,"
            b"City,State,Security contact email\n"
            b"example.gov,Federal,Example Agency,Example Office,Washington,DC,"
            b"security@example.gov\n"
        )

        dataframe = asm_sync_local_helpers.dotgov_domains()

        self.assertEqual(dataframe.loc[0, "domain_name"], "example.gov")
        self.assertEqual(dataframe.loc[0, "agency"], "Example Agency")
        self.assertIn("security_contact_email", dataframe.columns)
        get_mock.assert_called_once_with(
            "https://raw.githubusercontent.com/cisagov/dotgov-data/main/current-federal.csv",
            timeout=60,
        )


class RetrieveAllCyhyDataTests(unittest.TestCase):
    """Verify CyHy request documents are transformed into PE input records."""

    @patch.object(asm_sync_local_helpers.datetime, "datetime")
    def test_transforms_organizations_assets_contacts_and_sectors(self, datetime_mock):
        """Split organization and sector documents into the expected return values."""
        datetime_mock.today.return_value.date.return_value = "2026-08-19"
        organization = {
            "_id": "CHILD",
            "key": "org-key",
            "retired": False,
            "report_types": ["CYHY", "BOD"],
            "period_start": "2026-01-01",
            "children": ["SUBCHILD"],
            "networks": ["192.0.2.0/24", "192.0.2.1"],
            "agency": {
                "name": "Child Agency",
                "type": "Federal",
                "location": {"state": "DC", "country": "US"},
                "contacts": [
                    {
                        "name": "Person",
                        "email": "person@example.gov",
                        "phone": "555-0100",
                    }
                ],
            },
        }
        sector = {
            "_id": "SECTOR",
            "key": "sector-key",
            "children": ["CHILD"],
            "agency": {
                "name": "Sector",
                "acronym": "SEC",
                "contacts": [
                    {
                        "name": "Distribution",
                        "email": "distro@example.gov",
                        "type": "DISTRO",
                    }
                ],
            },
        }
        collection = MagicMock()
        collection.find.side_effect = [
            [{"_id": "EXECUTIVE", "children": ["CHILD"]}],
            [organization, sector],
        ]
        cyhy_database = {"requests": collection}

        result = asm_sync_local_helpers.retrieve_all_cyhy_data(cyhy_database)

        assets_df, relationships, contacts_df, agencies_df, sectors, sector_ids = result
        self.assertEqual(len(assets_df), 2)
        self.assertEqual(set(assets_df["type"]), {"cidr", "ip"})
        self.assertEqual(relationships, {"SUBCHILD": "CHILD"})
        self.assertEqual(contacts_df.loc[0, "contact_type"], "unspecified")
        self.assertTrue(agencies_df.loc[0, "fceb"])
        self.assertEqual(sectors[0]["email"], "distro@example.gov")
        self.assertEqual(sector_ids, ["SECTOR"])


class InsertAllCyhyDataTests(unittest.TestCase):
    """Verify processed CyHy records are passed through the insertion workflow."""

    def test_inserts_data_and_updates_relationship_statuses(self):
        """Insert each dataset and derive sector, parent, scan, and FCEB relationships."""
        connection = MagicMock(name="connection")
        assets_df = asm_sync_local_helpers.pd.DataFrame([{"network": "192.0.2.0/24"}])
        contacts_df = asm_sync_local_helpers.pd.DataFrame(
            [
                {
                    "org_id": "CHILD",
                    "name": "Person",
                    "contact_type": "DISTRO",
                    "email": "person@example.gov",
                },
                {
                    "org_id": "CHILD",
                    "name": "Person",
                    "contact_type": "DISTRO",
                    "email": "person@example.gov",
                },
            ]
        )
        agencies_df = asm_sync_local_helpers.pd.DataFrame(
            [{"cyhy_db_name": "CHILD"}, {"cyhy_db_name": "PARENT"}]
        )
        sectors = [
            {
                "id": "SECTOR",
                "acronym": "SEC",
                "children": ["CHILD", "SUB"],
            }
        ]
        pe_sectors = asm_sync_local_helpers.pd.DataFrame(
            [
                {
                    "id": "SECTOR",
                    "acronym": "SEC",
                    "sector_uid": "sector-uid",
                    "run_scorecards": True,
                },
                {
                    "id": "SUB",
                    "acronym": "SUB",
                    "sector_uid": "subsector-uid",
                    "run_scorecards": False,
                },
            ]
        )
        pe_orgs = asm_sync_local_helpers.pd.DataFrame(
            [
                {
                    "cyhy_db_name": "CHILD",
                    "organizations_uid": "child-uid",
                    "report_on": False,
                    "fceb": False,
                },
                {
                    "cyhy_db_name": "PARENT",
                    "organizations_uid": "parent-uid",
                    "report_on": True,
                    "fceb": True,
                },
            ]
        )

        patch_names = [
            "add_sector_hierachy",
            "dotgov_domains",
            "insert_assets",
            "insert_contacts",
            "insert_cyhy_agencies",
            "insert_dotgov_domains",
            "insert_sector_org_relationship",
            "insert_sectors",
            "update_child_parent_orgs",
            "update_fceb_child_status",
            "update_scan_status",
        ]
        patchers = {
            name: patch.object(asm_sync_local_helpers, name) for name in patch_names
        }
        mocks = {name: patcher.start() for name, patcher in patchers.items()}
        self.addCleanup(
            lambda: [patcher.stop() for patcher in reversed(list(patchers.values()))]
        )
        mocks["dotgov_domains"].return_value = MagicMock(name="dotgov_df")

        with (
            patch.object(
                asm_sync_local_helpers,
                "query_pe_sectors",
                return_value=pe_sectors,
            ),
            patch.object(
                asm_sync_local_helpers,
                "query_pe_orgs",
                return_value=pe_orgs,
            ),
            patch.dict(
                os.environ,
                {"PE_DB_PASSWORD_KEY": "database-key"},
                clear=False,
            ),
        ):
            asm_sync_local_helpers.insert_all_cyhy_data(
                connection,
                assets_df,
                {"CHILD": "PARENT"},
                contacts_df,
                agencies_df,
                sectors,
                ["SECTOR", "SUB"],
            )

        mocks["insert_sectors"].assert_called_once_with(
            connection,
            "database-key",
            sectors,
        )
        self.assertEqual(agencies_df["scorecard"].tolist(), [True, False])
        mocks["insert_assets"].assert_called_once_with(connection, assets_df)
        self.assertEqual(len(contacts_df), 1)
        mocks["insert_contacts"].assert_called_once_with(connection, contacts_df)
        mocks["insert_cyhy_agencies"].assert_called_once_with(
            connection,
            "database-key",
            agencies_df,
        )
        mocks["insert_sector_org_relationship"].assert_called_once()
        mocks["add_sector_hierachy"].assert_called_once_with(
            connection,
            "subsector-uid",
            "sector-uid",
        )
        mocks["update_child_parent_orgs"].assert_called_once_with(
            connection,
            "parent-uid",
            "CHILD",
        )
        mocks["update_scan_status"].assert_called_once_with(connection, "CHILD")
        mocks["update_fceb_child_status"].assert_called_once_with(
            connection,
            "CHILD",
        )
        mocks["insert_dotgov_domains"].assert_called_once_with(
            connection,
            mocks["dotgov_domains"].return_value,
        )


if __name__ == "__main__":
    unittest.main()
