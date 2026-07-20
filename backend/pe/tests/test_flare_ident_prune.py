"""Unit tests for flare_ident_prune data collection script."""

# Standard Python Libraries
import os
import socket
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
import pandas as pd

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")
os.environ.setdefault("FLARE_TENANT_ID", "12345")
os.environ.setdefault("FLARE_API_KEY", "fake-flare-key")

# Third-Party Libraries
from pe_source.flare.flare_helpers import get_flare_token
from pe_source.flare_ident_prune.flare_ident_prune import (
    check_domains_responsive,
    flare_identifiers_endpoint,
    parse_domain_idents,
    run_flare_ident_prune,
    toggle_ident,
)


class TestFlareHelpers(unittest.TestCase):
    """Verify flare_helpers function behavior."""

    @patch("pe_source.flare.flare_helpers.requests.post")
    @patch.dict(
        os.environ,
        {
            "FLARE_TENANT_ID": "12345",
            "FLARE_API_KEY": "fake-flare-key",
        },
    )
    def test_get_flare_token(self, mock_post):
        """Test get_flare_token returns token on success."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "mock_flare_token"}
        mock_post.return_value = mock_response
        # Call function
        token = get_flare_token()
        # Assert
        self.assertEqual(token, "mock_flare_token")
        mock_post.assert_called_once_with(
            "https://api.flare.io/tokens/generate",
            data='{"tenant_id": 12345}',
            headers={"Content-Type": "application/json"},
            auth=unittest.mock.ANY,
            timeout=60,
        )

    @patch("pe_source.flare.flare_helpers.time.sleep")
    @patch("pe_source.flare.flare_helpers.requests.post")
    @patch.dict(
        os.environ,
        {
            "FLARE_TENANT_ID": "12345",
            "FLARE_API_KEY": "fake-flare-key",
        },
    )
    def test_get_flare_token_retry(self, mock_post, mock_sleep):
        """Test get_flare_token retries on failure then succeeds."""
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.json.return_value = {"token": "retry_token"}
        mock_post.side_effect = [mock_fail, mock_success]
        # Call function
        token = get_flare_token()
        # Assert
        self.assertEqual(token, "retry_token")
        self.assertEqual(mock_post.call_count, 2)

    @patch("pe_source.flare.flare_helpers.time.sleep")
    @patch("pe_source.flare.flare_helpers.requests.post")
    @patch.dict(
        os.environ,
        {
            "FLARE_TENANT_ID": "12345",
            "FLARE_API_KEY": "fake-flare-key",
        },
    )
    def test_get_flare_token_all_retries_exhausted(self, mock_post, mock_sleep):
        """Test get_flare_token returns None when all retries fail."""
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        mock_post.return_value = mock_fail
        # Call function
        token = get_flare_token()
        # Assert
        self.assertIsNone(token)
        self.assertEqual(mock_post.call_count, 6)  # 1 initial + 5 retries

    def test_get_flare_token_missing_api_key(self):
        """Test get_flare_token returns None when API key is not set."""
        with patch.dict(os.environ, {"FLARE_API_KEY": ""}, clear=False):
            token = get_flare_token()
        self.assertIsNone(token)


class TestFlareIdentPruneHelpers(unittest.TestCase):
    """Verify flare_ident_prune helper function behavior."""

    @patch("pe_source.flare_ident_prune.flare_ident_prune.create_retry_session")
    def test_flare_identifiers_endpoint(self, mock_create_session):
        """Test flare_identifiers_endpoint returns token and response."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        # Call function
        token = "mock_token"  # nosec
        params = {"source_group": "SYSTEM", "types": ["domain"], "size": 100}
        result_token, result_resp = flare_identifiers_endpoint(token, params)
        # Assert
        self.assertEqual(result_token, token)
        self.assertEqual(result_resp, mock_response)
        mock_session.get.assert_called_once_with(
            "https://api.flare.io/firework/v3/identifiers/",
            headers={
                "Authorization": "Bearer mock_token",
                "Content-Type": "application/json",
            },
            params=params,
            timeout=60,
        )

    @patch("pe_source.flare_ident_prune.flare_ident_prune.create_retry_session")
    def test_flare_identifiers_endpoint_401(self, mock_create_session):
        """Test flare_identifiers_endpoint returns response on 401 for token refresh."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = __import__(
            "requests"
        ).exceptions.HTTPError(response=mock_response)
        mock_session.get.return_value = mock_response
        mock_create_session.return_value = mock_session
        # Call function
        token = "expired_token"  # nosec
        result_token, result_resp = flare_identifiers_endpoint(token, {})
        # Assert - should return the response so caller can handle 401
        self.assertEqual(result_resp, mock_response)

    def test_parse_domain_idents(self):
        """Test parse_domain_idents parses API response correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "next": "cursor_abc",
            "total_count": 200,
            "items": [
                {
                    "id": 1001,
                    "type": "domain",
                    "name": "sub1.example.gov",
                    "source": "SYSTEM",
                    "is_disabled": False,
                },
                {
                    "id": 1002,
                    "type": "domain",
                    "name": "sub2.example.gov",
                    "source": "SYSTEM",
                    "is_disabled": True,
                },
            ],
        }
        # Call function
        result = parse_domain_idents(mock_response)
        # Assert
        self.assertEqual(result["next"], "cursor_abc")
        self.assertEqual(result["total_count"], 200)
        self.assertEqual(len(result["domains"]), 2)
        self.assertEqual(result["domains"][0]["id"], 1001)
        self.assertEqual(result["domains"][0]["value"], "sub1.example.gov")
        self.assertTrue(result["domains"][0]["curr_enabled"])
        self.assertFalse(result["domains"][1]["curr_enabled"])
        self.assertFalse(result["domains"][0]["detected_resolvable"])

    @patch("pe_source.flare_ident_prune.flare_ident_prune.asyncio.run")
    @patch("pe_source.flare_ident_prune.flare_ident_prune.socket.gethostbyname")
    def test_check_domains_responsive(self, mock_gethostbyname, mock_asyncio_run):
        """Test check_domains_responsive classifies domains correctly."""
        # Setup: 3 domains with different states
        domain_list = [
            {
                "id": 1,
                "type": "domain",
                "value": "responsive.gov",
                "ip": None,
                "source": "SYSTEM",
                "curr_enabled": True,
                "detected_resolvable": False,
            },
            {
                "id": 2,
                "type": "domain",
                "value": "unresponsive.gov",
                "ip": None,
                "source": "SYSTEM",
                "curr_enabled": True,
                "detected_resolvable": False,
            },
            {
                "id": 3,
                "type": "domain",
                "value": "disabled-but-responsive.gov",
                "ip": None,
                "source": "SYSTEM",
                "curr_enabled": False,
                "detected_resolvable": False,
            },
        ]

        # Mock DNS resolution
        def gethostbyname_side_effect(domain):
            if domain == "responsive.gov":
                return "1.1.1.1"
            if domain == "disabled-but-responsive.gov":
                return "3.3.3.3"
            raise socket.gaierror("Name or service not known")

        mock_gethostbyname.side_effect = gethostbyname_side_effect

        # Mock ICMP ping results
        mock_asyncio_run.return_value = [
            {"ip": "1.1.1.1", "detected_reachable": True, "response_delay": 0.01},
            {"ip": "3.3.3.3", "detected_reachable": True, "response_delay": 0.02},
        ]

        # Call function
        enable_list, disable_list, result_df = check_domains_responsive(domain_list)

        # Assert
        # unresponsive.gov: enabled + not responsive → DISABLE
        self.assertEqual(len(disable_list), 1)
        self.assertEqual(disable_list[0]["value"], "unresponsive.gov")
        # disabled-but-responsive.gov: disabled + responsive → ENABLE
        self.assertEqual(len(enable_list), 1)
        self.assertEqual(enable_list[0]["value"], "disabled-but-responsive.gov")
        # responsive.gov: enabled + responsive → NO ACTION
        no_action = result_df.loc[result_df["required_action"] == "NO ACTION"]
        self.assertEqual(len(no_action), 1)
        self.assertEqual(no_action.iloc[0]["value"], "responsive.gov")

    @patch("pe_source.flare_ident_prune.flare_ident_prune.create_retry_session")
    def test_toggle_ident_enable(self, mock_create_session):
        """Test toggle_ident sends correct payload to enable."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session
        # Call function
        token, resp = toggle_ident("mock_token", 1001, active=True)
        # Assert
        mock_session.post.assert_called_once_with(
            "https://api.flare.io/firework/v2/assets/1001/toggle",
            json={"is_disabled": False},
            headers={
                "Authorization": "Bearer mock_token",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

    @patch("pe_source.flare_ident_prune.flare_ident_prune.create_retry_session")
    def test_toggle_ident_disable(self, mock_create_session):
        """Test toggle_ident sends correct payload to disable."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_session.post.return_value = mock_response
        mock_create_session.return_value = mock_session
        # Call function
        token, resp = toggle_ident("mock_token", 1002, active=False)
        # Assert
        mock_session.post.assert_called_once_with(
            "https://api.flare.io/firework/v2/assets/1002/toggle",
            json={"is_disabled": True},
            headers={
                "Authorization": "Bearer mock_token",
                "Content-Type": "application/json",
            },
            timeout=60,
        )


class TestRunFlareIdentPrune(unittest.TestCase):
    """Verify run_flare_ident_prune main script function."""

    @patch("pe_source.flare_ident_prune.flare_ident_prune.update_ident_lists")
    @patch("pe_source.flare_ident_prune.flare_ident_prune.check_domains_responsive")
    @patch("pe_source.flare_ident_prune.flare_ident_prune.get_all_autoenum_domains")
    @patch("pe_source.flare_ident_prune.flare_ident_prune.get_orgs")
    def test_run_flare_ident_prune_all_orgs(
        self,
        mock_get_orgs,
        mock_get_domains,
        mock_check_responsive,
        mock_update_lists,
    ):
        """Test run_flare_ident_prune with orgs_list='all'."""
        # Mock orgs
        mock_get_orgs.return_value = [
            {
                "organizations_uid": "uid-1",
                "cyhy_db_name": "org_a",
                "report_on": True,
                "demo": False,
            },
            {
                "organizations_uid": "uid-2",
                "cyhy_db_name": "org_b",
                "report_on": False,
                "demo": True,
            },
        ]
        # Mock domain retrieval (enabled + disabled calls)
        mock_get_domains.side_effect = [
            [
                {
                    "id": 1,
                    "type": "domain",
                    "value": "test1.gov",
                    "ip": None,
                    "source": "SYSTEM",
                    "curr_enabled": True,
                    "detected_resolvable": False,
                }
            ],
            [
                {
                    "id": 2,
                    "type": "domain",
                    "value": "test2.gov",
                    "ip": None,
                    "source": "SYSTEM",
                    "curr_enabled": False,
                    "detected_resolvable": False,
                }
            ],
        ]
        # Mock responsiveness check
        mock_results_df = pd.DataFrame(
            [
                {"id": 1, "value": "test1.gov", "required_action": "DISABLE"},
                {"id": 2, "value": "test2.gov", "required_action": "ENABLE"},
            ]
        )
        mock_check_responsive.return_value = (
            [{"id": 2, "value": "test2.gov"}],
            [{"id": 1, "value": "test1.gov"}],
            mock_results_df,
        )
        # Call function
        run_flare_ident_prune("all")
        # Assert
        mock_get_orgs.assert_called_once()
        self.assertEqual(mock_get_domains.call_count, 2)
        mock_check_responsive.assert_called_once()
        mock_update_lists.assert_called_once_with(
            [{"id": 2, "value": "test2.gov"}],
            [{"id": 1, "value": "test1.gov"}],
        )

    @patch("pe_source.flare_ident_prune.flare_ident_prune.update_ident_lists")
    @patch("pe_source.flare_ident_prune.flare_ident_prune.check_domains_responsive")
    @patch("pe_source.flare_ident_prune.flare_ident_prune.get_all_autoenum_domains")
    @patch("pe_source.flare_ident_prune.flare_ident_prune.get_orgs")
    def test_run_flare_ident_prune_excluded_domains(
        self,
        mock_get_orgs,
        mock_get_domains,
        mock_check_responsive,
        mock_update_lists,
    ):
        """Test that protected domains are excluded from processing."""
        mock_get_orgs.return_value = [
            {
                "organizations_uid": "uid-1",
                "cyhy_db_name": "org_a",
                "report_on": True,
                "demo": False,
            },
        ]
        # Include a protected domain that should be filtered out
        mock_get_domains.side_effect = [
            [
                {
                    "id": 1,
                    "type": "domain",
                    "value": "sub.doj.gov",
                    "ip": None,
                    "source": "SYSTEM",
                    "curr_enabled": True,
                    "detected_resolvable": False,
                },
                {
                    "id": 2,
                    "type": "domain",
                    "value": "normal.example.gov",
                    "ip": None,
                    "source": "SYSTEM",
                    "curr_enabled": True,
                    "detected_resolvable": False,
                },
            ],
            [],  # disabled list empty
        ]
        # Mock responsiveness - only normal.example.gov should reach here
        mock_results_df = pd.DataFrame(
            [{"id": 2, "value": "normal.example.gov", "required_action": "NO ACTION"}]
        )
        mock_check_responsive.return_value = ([], [], mock_results_df)
        # Call function
        run_flare_ident_prune("all")
        # Assert - check_domains_responsive should only receive the non-excluded domain
        called_domains = mock_check_responsive.call_args[0][0]
        domain_values = [d["value"] for d in called_domains]
        self.assertNotIn("sub.doj.gov", domain_values)
        self.assertIn("normal.example.gov", domain_values)


if __name__ == "__main__":
    unittest.main()
