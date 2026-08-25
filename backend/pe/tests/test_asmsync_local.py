"""Tests for the local ASM Sync step."""

# Standard Python Libraries
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
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
    """Verify the local workflow retrieves CyHy data and uploads it to S3."""

    def test_retrieves_and_uploads_all_datasets(self):
        """Pass all six retrieved dataframes to the S3 upload helper."""
        cyhy_connection = MagicMock(name="cyhy_connection")
        cyhy_results = [
            MagicMock(name="dataframe_{}".format(index)) for index in range(6)
        ]
        input_values = ["/keys/cyhy.pem", "key-password", "reports-bucket"]
        environment_after_run = {}

        with (
            patch("builtins.input", side_effect=input_values) as input_mock,
            patch.object(
                asm_sync_local,
                "get_ssm_parameter",
                side_effect=lambda parameter: "resolved:{}".format(parameter),
            ) as ssm_mock,
            patch.object(
                asm_sync_local, "cyhy_db_connect", return_value=cyhy_connection
            ) as connect_mock,
            patch.object(
                asm_sync_local,
                "retrieve_all_cyhy_data",
                return_value=cyhy_results,
            ) as retrieve_mock,
            patch.object(asm_sync_local, "upload_all_cyhy_data") as upload_mock,
            patch.object(asm_sync_local.time, "time", return_value=100.0),
            patch.object(asm_sync_local.subprocess, "run") as subprocess_mock,
            patch.dict(os.environ, {}, clear=False),
        ):
            asm_sync_local.run_asm_sync_local()
            environment_after_run = {
                "CYHY_DB_PKEY_LOCATION": os.environ["CYHY_DB_PKEY_LOCATION"],
                "PE_S3_BUCKET": os.environ["PE_S3_BUCKET"],
                "WHOISXML_KEY": os.environ["WHOISXML_KEY"],
            }

        self.assertEqual(input_mock.call_count, 3)
        self.assertEqual(ssm_mock.call_count, 2)
        connect_mock.assert_called_once_with()
        retrieve_mock.assert_called_once_with(cyhy_connection)
        upload_mock.assert_called_once_with(*cyhy_results)
        subprocess_mock.assert_called_once_with(
            ["/usr/bin/killall", "SCREEN"], check=True, timeout=30
        )
        self.assertEqual(
            environment_after_run["CYHY_DB_PKEY_LOCATION"], "/keys/cyhy.pem"
        )
        self.assertEqual(environment_after_run["PE_S3_BUCKET"], "reports-bucket")
        self.assertEqual(
            environment_after_run["WHOISXML_KEY"],
            "resolved:/crossfeed/staging/WHOIS_XML_KEY",
        )


class MainTests(unittest.TestCase):
    """Verify the command entry point starts the local workflow."""

    @patch.object(asm_sync_local, "run_asm_sync_local")
    def test_main_runs_local_workflow(self, run_mock):
        """Invoke the local workflow without obsolete database arguments."""
        asm_sync_local.main()

        run_mock.assert_called_once_with()


class GetSsmParameterTests(unittest.TestCase):
    """Verify encrypted SSM parameters are retrieved and errors propagate."""

    @patch.object(asm_sync_local_helpers.boto3, "client")
    def test_returns_decrypted_parameter_value(self, client_mock):
        """Request decryption and return the nested parameter value."""
        ssm_client = client_mock.return_value
        ssm_client.get_parameter.return_value = {"Parameter": {"Value": "secret"}}

        value = asm_sync_local_helpers.get_ssm_parameter("/crossfeed/test/key")

        self.assertEqual(value, "secret")
        client_mock.assert_called_once_with("ssm")
        ssm_client.get_parameter.assert_called_once_with(
            Name="/crossfeed/test/key", WithDecryption=True
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


class CyhyDatabaseConnectionTests(unittest.TestCase):
    """Verify CyHy connection setup uses the configured MongoDB endpoint."""

    @patch.object(asm_sync_local_helpers.Path, "resolve")
    @patch.object(asm_sync_local_helpers.time, "sleep")
    @patch.object(asm_sync_local_helpers.subprocess, "run")
    @patch.object(asm_sync_local_helpers, "MongoClient")
    def test_connects_through_cyhy_tunnel(
        self, mongo_mock, subprocess_mock, sleep_mock, resolve_mock
    ):
        """Start the tunnel and return the CyHy Mongo database."""
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
            ["/resolved/screenConnectCyHy"], check=True, timeout=30
        )
        sleep_mock.assert_called_once_with(3)
        mongo_mock.assert_called_once_with(
            "mongodb://cyhy_ops:password@localhost:27017/cyhy"
        )


class RetrieveAllCyhyDataTests(unittest.TestCase):
    """Verify CyHy documents are transformed into six upload dataframes."""

    @patch.object(asm_sync_local_helpers.datetime, "datetime")
    def test_transforms_organizations_assets_contacts_and_sectors(self, datetime_mock):
        """Split organization and sector documents into expected dataframes."""
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

        result = asm_sync_local_helpers.retrieve_all_cyhy_data({"requests": collection})

        orgs_df, assets_df, contacts_df, relationships_df, sectors_df, ids_df = result
        self.assertEqual(orgs_df.loc[0, "cyhy_db_name"], "CHILD")
        self.assertEqual(len(assets_df), 2)
        self.assertEqual(set(assets_df["type"]), {"cidr", "ip"})
        self.assertEqual(contacts_df.loc[0, "contact_type"], "unspecified")
        self.assertEqual(
            relationships_df.to_dict("records"),
            [{"child": "SUBCHILD", "parent": "CHILD"}],
        )
        self.assertEqual(sectors_df.loc[0, "email"], "distro@example.gov")
        self.assertEqual(ids_df.loc[0, "sectors"], "SECTOR")


class UploadCyhyDataTests(unittest.TestCase):
    """Verify generated CSV files are uploaded to the configured S3 bucket."""

    def test_uploads_file_under_dated_s3_prefix(self):
        """Build the expected object key from the date and local filename."""
        s3_client = MagicMock(name="s3_client")
        with TemporaryDirectory() as temporary_directory:
            local_file = str(Path(temporary_directory) / "cyhy_orgs_2026-08-25.csv")

            asm_sync_local_helpers.upload_cyhy_data_to_s3(
                s3_client,
                "reports-bucket",
                "2026-08-25",
                local_file,
            )

            s3_client.upload_file.assert_called_once_with(
                local_file,
                "reports-bucket",
                "asm_sync_local_runs/2026-08-25/cyhy_orgs_2026-08-25.csv",
            )

    @patch.object(asm_sync_local_helpers, "upload_cyhy_data_to_s3")
    @patch.object(asm_sync_local_helpers.boto3, "client")
    @patch.object(asm_sync_local_helpers.datetime, "datetime")
    @patch.object(asm_sync_local_helpers.Path, "resolve")
    def test_writes_and_uploads_all_six_dataframes(
        self, resolve_mock, datetime_mock, client_mock, upload_mock
    ):
        """Serialize every dataset and send every resulting path to S3."""
        with TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            resolve_mock.return_value = temporary_path / "asm_sync_local_helpers.py"
            datetime_mock.now.return_value.strftime.return_value = "2026-08-25"
            dataframes = [
                MagicMock(name="dataframe_{}".format(index)) for index in range(6)
            ]

            with patch.dict(
                os.environ,
                {"PE_S3_BUCKET": "reports-bucket"},
                clear=False,
            ):
                asm_sync_local_helpers.upload_all_cyhy_data(*dataframes)

            output_directory = temporary_path / "asm_sync_local_runs" / "2026-08-25"
            expected_paths = [
                str(output_directory / "cyhy_orgs_2026-08-25.csv"),
                str(output_directory / "cyhy_assets_2026-08-25.csv"),
                str(output_directory / "cyhy_contacts_2026-08-25.csv"),
                str(output_directory / "cyhy_child_parent_2026-08-25.csv"),
                str(output_directory / "cyhy_sectors_info_2026-08-25.csv"),
                str(output_directory / "cyhy_sectors_2026-08-25.csv"),
            ]
            for dataframe, expected_path in zip(dataframes, expected_paths):
                dataframe.to_csv.assert_called_once_with(expected_path)

            self.assertEqual(
                upload_mock.call_args_list,
                [
                    call(
                        client_mock.return_value,
                        "reports-bucket",
                        "2026-08-25",
                        expected_path,
                    )
                    for expected_path in expected_paths
                ],
            )


if __name__ == "__main__":
    unittest.main()
