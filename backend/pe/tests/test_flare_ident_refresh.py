"""Unit tests for flare identifier refresh script."""

# Standard Python Libraries
import asyncio
import os
import unittest
from unittest.mock import ANY, AsyncMock, MagicMock, call, patch

# Third-Party Libraries
import pandas as pd

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")
os.environ.setdefault("FLARE_TENANT_ID", "12345")
os.environ.setdefault("FLARE_API_KEY", "fake-flare-key")

# Third-Party Libraries
from pe_source.flare_ident_refresh.flare_ident_refresh import (
    check_ident_group_exists,
    check_ip_list_reachable,
    check_ip_reachable,
    create_domain_ident,
    create_exec_ident,
    create_flare_identifer,
    create_ident_group,
    create_ip_ident,
    create_keyword_ident,
    delete_flare_identifier,
    delete_ident_list,
    format_exec_data,
    get_flare_token,
    get_ident_by_group_id,
    get_ident_group_info,
    run_flare_ident_refresh,
)

MODULE = "pe_source.flare_ident_refresh.flare_ident_refresh"


class FlareApiTests(unittest.TestCase):
    """Verify direct interactions with the Flare API."""

    @patch("{}.requests.post".format(MODULE))
    def test_get_flare_token_returns_token(self, mock_post):
        """A successful token response should return its token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "mock-token"}
        mock_post.return_value = mock_response

        result = get_flare_token()

        self.assertEqual(result, "mock-token")
        mock_post.assert_called_once_with(
            "https://api.flare.io/tokens/generate",
            data='{"tenant_id": 12345}',
            headers={"Content-Type": "application/json"},
            auth=ANY,
            timeout=60,
        )

    @patch("{}.time.sleep".format(MODULE))
    @patch("{}.requests.post".format(MODULE))
    def test_get_flare_token_retries_then_succeeds(
        self,
        mock_post,
        mock_sleep,
    ):
        """A transient token failure should be retried."""
        failed_response = MagicMock()
        failed_response.status_code = 500

        successful_response = MagicMock()
        successful_response.status_code = 200
        successful_response.json.return_value = {"token": "retry-token"}

        mock_post.side_effect = [failed_response, successful_response]

        result = get_flare_token()

        self.assertEqual(result, "retry-token")
        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called_once_with(3)

    @patch("{}.time.sleep".format(MODULE))
    @patch("{}.requests.post".format(MODULE))
    def test_get_flare_token_returns_none_after_all_retries(
        self,
        mock_post,
        mock_sleep,
    ):
        """An unsuccessful token request should stop after five retries."""
        failed_response = MagicMock()
        failed_response.status_code = 500
        mock_post.return_value = failed_response

        result = get_flare_token()

        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 6)
        self.assertEqual(mock_sleep.call_count, 5)

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.get".format(MODULE))
    def test_get_ident_group_info_returns_matching_child_group(
        self,
        mock_get,
        _mock_get_token,
    ):
        """The matching organization under the PE parent should be returned."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assets_groups": [
                {
                    "id": 10,
                    "name": "TEST_ORG",
                    "parent_group_id": 999,
                },
                {
                    "id": 20,
                    "name": "TEST_ORG",
                    "parent_group_id": 191286,
                },
            ]
        }
        mock_get.return_value = mock_response

        result = get_ident_group_info("TEST_ORG")

        self.assertEqual(result, {"name": "TEST_ORG", "id": 20})
        mock_get.assert_called_once_with(
            "https://api.flare.io/firework/v2/assets/groups/",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer mock-token",
            },
            timeout=60,
        )

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.get".format(MODULE))
    def test_get_ident_group_info_returns_none_after_failures(
        self,
        mock_get,
        _mock_get_token,
    ):
        """Group retrieval should return None after all attempts fail."""
        failed_response = MagicMock()
        failed_response.status_code = 503
        mock_get.return_value = failed_response

        with patch("{}.time.sleep".format(MODULE)) as mock_sleep:
            result = get_ident_group_info("TEST_ORG")

        self.assertIsNone(result)
        self.assertEqual(mock_get.call_count, 6)
        self.assertEqual(mock_sleep.call_count, 5)

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.get".format(MODULE))
    def test_check_ident_group_exists_returns_true(
        self,
        mock_get,
        _mock_get_token,
    ):
        """An organization under the PE parent should be detected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assets_groups": [
                {
                    "id": 20,
                    "name": "TEST_ORG",
                    "parent_group_id": 191286,
                }
            ]
        }
        mock_get.return_value = mock_response

        self.assertTrue(check_ident_group_exists("TEST_ORG"))

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.get".format(MODULE))
    def test_check_ident_group_exists_returns_false(
        self,
        mock_get,
        _mock_get_token,
    ):
        """An organization absent from the PE parent should not be detected."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "assets_groups": [
                {
                    "id": 20,
                    "name": "OTHER_ORG",
                    "parent_group_id": 191286,
                }
            ]
        }
        mock_get.return_value = mock_response

        self.assertFalse(check_ident_group_exists("TEST_ORG"))

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.post".format(MODULE))
    def test_create_ident_group_uses_expected_payload(
        self,
        mock_post,
        _mock_get_token,
    ):
        """A new organization group should be created under the PE parent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = create_ident_group("TEST_ORG")

        self.assertIs(result, mock_response)
        mock_post.assert_called_once_with(
            "https://api.flare.io/firework/v2/assets/groups/",
            json={
                "parent_group_id": 191286,
                "name": "TEST_ORG",
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer mock-token",
            },
            timeout=60,
        )

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.get".format(MODULE))
    def test_get_ident_by_group_id_formats_identifiers(
        self,
        mock_get,
        _mock_get_token,
    ):
        """Flare identifier fields should be normalized for comparison."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "id": 1,
                    "name": "example.gov",
                    "type": "domain",
                },
                {
                    "id": 2,
                    "name": "Example Agency",
                    "type": "keyword",
                },
            ]
        }
        mock_get.return_value = mock_response

        result = get_ident_by_group_id(123)

        self.assertEqual(
            result,
            [
                {
                    "id": 1,
                    "value": "example.gov",
                    "type": "domain",
                },
                {
                    "id": 2,
                    "value": "Example Agency",
                    "type": "keyword",
                },
            ],
        )
        mock_get.assert_called_once_with(
            "https://api.flare.io/firework/v3/identifiers/",
            headers={"Authorization": "Bearer mock-token"},
            params={"parent_group_id": 123},
            timeout=60,
        )

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.get".format(MODULE))
    def test_get_ident_by_group_id_returns_placeholder_when_empty(
        self,
        mock_get,
        _mock_get_token,
    ):
        """An empty Flare group should produce the expected placeholder."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        result = get_ident_by_group_id(123)

        self.assertEqual(
            result,
            [
                {
                    "id": None,
                    "value": None,
                    "type": None,
                }
            ],
        )

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.post".format(MODULE))
    def test_create_flare_identifier_posts_payload(
        self,
        mock_post,
        _mock_get_token,
    ):
        """Identifier creation should send the supplied payload."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        payload = {
            "assets_group_id": 123,
            "name": "example.gov",
            "type": "domain",
        }

        create_flare_identifer(payload)

        mock_post.assert_called_once_with(
            "https://api.flare.io/firework/v2/assets/",
            json=payload,
            headers={
                "Authorization": "Bearer mock-token",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

    @patch("{}.get_flare_token".format(MODULE), return_value="mock-token")
    @patch("{}.requests.delete".format(MODULE))
    def test_delete_flare_identifier_uses_identifier_id(
        self,
        mock_delete,
        _mock_get_token,
    ):
        """Identifier deletion should address the requested identifier."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response

        delete_flare_identifier(456)

        mock_delete.assert_called_once_with(
            "https://api.flare.io/firework/v2/assets/456",
            headers={
                "Authorization": "Bearer mock-token",
                "Content-Type": "application/json",
            },
            timeout=60,
        )


class IpReachabilityTests(unittest.TestCase):
    """Verify asynchronous IP reachability checks."""

    @patch("{}.aioping.ping".format(MODULE), new_callable=AsyncMock)
    def test_check_ip_reachable_returns_success(self, mock_ping):
        """A successful ping should mark the address reachable."""
        mock_ping.return_value = 0.125
        semaphore = asyncio.Semaphore(1)

        result = asyncio.run(
            check_ip_reachable(
                semaphore,
                "192.0.2.10",
                count=1,
                timeout=2.0,
            )
        )

        self.assertEqual(
            result,
            {
                "ip": "192.0.2.10",
                "detected_reachable": True,
                "response_delay": 0.125,
            },
        )
        mock_ping.assert_awaited_once_with("192.0.2.10", timeout=2.0)

    @patch("{}.aioping.ping".format(MODULE), new_callable=AsyncMock)
    def test_check_ip_reachable_retries_timeout(self, mock_ping):
        """A timed-out ping should retry and eventually mark the IP unreachable."""
        mock_ping.side_effect = TimeoutError("timed out")
        semaphore = asyncio.Semaphore(1)

        result = asyncio.run(
            check_ip_reachable(
                semaphore,
                "192.0.2.20",
                count=3,
                timeout=1.0,
            )
        )

        self.assertEqual(
            result,
            {
                "ip": "192.0.2.20",
                "detected_reachable": False,
                "response_delay": None,
            },
        )
        self.assertEqual(mock_ping.await_count, 3)

    @patch(
        "{}.check_ip_reachable".format(MODULE),
        new_callable=AsyncMock,
    )
    def test_check_ip_list_reachable_returns_all_results(
        self,
        mock_check_ip,
    ):
        """The list helper should check every supplied IP address."""
        mock_check_ip.side_effect = [
            {
                "ip": "192.0.2.1",
                "detected_reachable": True,
                "response_delay": 0.1,
            },
            {
                "ip": "192.0.2.2",
                "detected_reachable": False,
                "response_delay": None,
            },
        ]

        result = asyncio.run(check_ip_list_reachable(["192.0.2.1", "192.0.2.2"]))

        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["detected_reachable"])
        self.assertFalse(result[1]["detected_reachable"])
        self.assertEqual(mock_check_ip.await_count, 2)


class IdentifierFormattingTests(unittest.TestCase):
    """Verify formatting and identifier payload construction."""

    def test_format_exec_data_formats_hyphenated_names(self):
        """Executive names should be converted into Flare name fields."""
        result = format_exec_data(
            [
                "jane-smith doe-jones",
                "john public",
            ]
        )

        self.assertEqual(
            result,
            [
                {
                    "first_name": "Jane Smith",
                    "last_name": "Doe Jones",
                },
                {
                    "first_name": "John",
                    "last_name": "Public",
                },
            ],
        )

    @patch("{}.create_flare_identifer".format(MODULE))
    def test_create_keyword_ident_builds_payloads(self, mock_create):
        """Each keyword should receive the expected Flare payload."""
        create_keyword_ident(["Example Agency", "Example Bureau"], 123)

        self.assertEqual(
            mock_create.call_args_list,
            [
                call(
                    {
                        "assets_group_id": 123,
                        "data": {"keyword": "Example Agency"},
                        "name": "Example Agency",
                        "search_types": [
                            "illicit_networks",
                            "open_web",
                        ],
                        "type": "keyword",
                    }
                ),
                call(
                    {
                        "assets_group_id": 123,
                        "data": {"keyword": "Example Bureau"},
                        "name": "Example Bureau",
                        "search_types": [
                            "illicit_networks",
                            "open_web",
                        ],
                        "type": "keyword",
                    }
                ),
            ],
        )

    @patch("{}.create_flare_identifer".format(MODULE))
    def test_create_domain_ident_builds_payload(self, mock_create):
        """A domain should receive the expected Flare payload."""
        create_domain_ident(["example.gov"], 123)

        mock_create.assert_called_once_with(
            {
                "assets_group_id": 123,
                "data": {"fqdn": "example.gov"},
                "name": "example.gov",
                "search_types": [
                    "illicit_networks",
                    "open_web",
                    "domain",
                    "leak",
                ],
                "type": "domain",
            }
        )

    @patch("{}.create_flare_identifer".format(MODULE))
    def test_create_exec_ident_builds_payload(self, mock_create):
        """An executive should receive strict first and last name fields."""
        create_exec_ident(
            [
                {
                    "first_name": "Jane",
                    "last_name": "Doe",
                }
            ],
            123,
        )

        mock_create.assert_called_once_with(
            {
                "assets_group_id": 123,
                "data": {
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "is_strict": True,
                },
                "name": "Jane Doe",
                "search_types": [
                    "illicit_networks",
                    "open_web",
                ],
                "type": "name",
            }
        )

    @patch("{}.create_flare_identifer".format(MODULE))
    def test_create_ip_ident_builds_payload(self, mock_create):
        """An IP address should receive the expected Flare payload."""
        create_ip_ident(["192.0.2.1"], 123)

        mock_create.assert_called_once_with(
            {
                "assets_group_id": 123,
                "data": {"ip": "192.0.2.1"},
                "name": "192.0.2.1",
                "search_types": [
                    "illicit_networks",
                    "open_web",
                ],
                "type": "ip",
            }
        )

    @patch("{}.delete_flare_identifier".format(MODULE))
    def test_delete_ident_list_deletes_every_matching_id(
        self,
        mock_delete,
    ):
        """Duplicate values should cause every matching ID to be deleted."""
        identifiers = pd.DataFrame(
            [
                {
                    "id": 10,
                    "value": "old.example.gov",
                    "type": "domain",
                },
                {
                    "id": 11,
                    "value": "old.example.gov",
                    "type": "domain",
                },
                {
                    "id": 12,
                    "value": "keep.example.gov",
                    "type": "domain",
                },
            ]
        )

        delete_ident_list(["old.example.gov"], identifiers)

        self.assertEqual(
            mock_delete.call_args_list,
            [
                call(10),
                call(11),
            ],
        )


class RunFlareIdentRefreshTests(unittest.TestCase):
    """Verify Flare identifier refresh orchestration."""

    def setUp(self):
        """Create representative organization data."""
        self.organizations = [
            {
                "cyhy_db_name": "B_ORG",
                "organizations_uid": "uid-b",
                "name": "B Agency",
                "report_on": True,
                "demo": False,
            },
            {
                "cyhy_db_name": "A_ORG",
                "organizations_uid": "uid-a",
                "name": "A Agency",
                "report_on": True,
                "demo": True,
            },
            {
                "cyhy_db_name": "C_ORG",
                "organizations_uid": "uid-c",
                "name": "C Agency",
                "report_on": False,
                "demo": True,
            },
        ]

    def _run_with_common_mocks(self, org_selection):
        """Run the refresh while replacing all external boundaries."""
        patches = [
            patch("{}.get_orgs".format(MODULE)),
            patch("{}.check_ident_group_exists".format(MODULE)),
            patch("{}.create_ident_group".format(MODULE)),
            patch("{}.get_ident_group_info".format(MODULE)),
            patch("{}.org_root_domains".format(MODULE)),
            patch("{}.get_execs_by_org_uid".format(MODULE)),
            patch("{}.get_resp_ips_by_org_abbrv".format(MODULE)),
            patch("{}.get_ident_by_group_id".format(MODULE)),
            patch("{}.create_keyword_ident".format(MODULE)),
            patch("{}.create_domain_ident".format(MODULE)),
            patch("{}.create_exec_ident".format(MODULE)),
            patch("{}.create_ip_ident".format(MODULE)),
            patch("{}.delete_ident_list".format(MODULE)),
            patch("{}.time.sleep".format(MODULE)),
        ]

        mocks = [active_patch.start() for active_patch in patches]
        self.addCleanup(
            lambda: [active_patch.stop() for active_patch in reversed(patches)]
        )

        (
            mock_get_orgs,
            mock_group_exists,
            mock_create_group,
            mock_get_group,
            mock_get_roots,
            mock_get_execs,
            mock_get_ips,
            mock_get_identifiers,
            mock_create_keyword,
            mock_create_domain,
            mock_create_exec,
            mock_create_ip,
            mock_delete,
            mock_sleep,
        ) = mocks

        mock_get_orgs.return_value = self.organizations
        mock_group_exists.return_value = True
        mock_get_group.return_value = {
            "name": "A_ORG",
            "id": 123,
        }
        mock_get_roots.return_value = [{"root_domain": "new.example.gov"}]
        mock_get_execs.return_value = pd.DataFrame(
            [
                {
                    "first_name": "Jane",
                    "last_name": "Doe",
                }
            ]
        )
        mock_get_ips.return_value = pd.DataFrame(
            [
                {
                    "cyhy_db_name": "A_ORG",
                    "ip": "192.0.2.1",
                }
            ]
        )
        mock_get_identifiers.return_value = [
            {
                "id": 1,
                "value": "Old Agency",
                "type": "keyword",
            },
            {
                "id": 2,
                "value": "old.example.gov",
                "type": "domain",
            },
            {
                "id": 3,
                "value": "Old Person",
                "type": "name",
            },
            {
                "id": 4,
                "value": "192.0.2.2",
                "type": "ip",
            },
        ]

        run_flare_ident_refresh(org_selection)

        return {
            "group_exists": mock_group_exists,
            "create_group": mock_create_group,
            "get_group": mock_get_group,
            "get_roots": mock_get_roots,
            "get_execs": mock_get_execs,
            "get_ips": mock_get_ips,
            "create_keyword": mock_create_keyword,
            "create_domain": mock_create_domain,
            "create_exec": mock_create_exec,
            "create_ip": mock_create_ip,
            "delete": mock_delete,
            "sleep": mock_sleep,
        }

    def test_run_refresh_filters_explicit_org_and_updates_differences(self):
        """Explicit selection should update only the matching organization."""
        mocks = self._run_with_common_mocks("A_ORG")

        mocks["group_exists"].assert_called_once_with("A_ORG")
        mocks["get_group"].assert_called_once_with("A_ORG")
        mocks["get_roots"].assert_called_once_with("uid-a")
        mocks["get_execs"].assert_called_once_with("uid-a")
        mocks["get_ips"].assert_called_once_with("A_ORG")

        mocks["create_keyword"].assert_called_once_with(
            ["a agency"],
            123,
        )
        mocks["create_domain"].assert_called_once_with(
            ["new.example.gov"],
            123,
        )
        mocks["create_exec"].assert_called_once_with(
            [
                {
                    "first_name": "Jane",
                    "last_name": "Doe",
                }
            ],
            123,
        )
        mocks["create_ip"].assert_called_once_with(
            ["192.0.2.1"],
            123,
        )

        self.assertEqual(mocks["delete"].call_count, 4)
        deleted_values = {
            delete_call.args[0][0] for delete_call in mocks["delete"].call_args_list
        }
        self.assertEqual(
            deleted_values,
            {
                "old agency",
                "old.example.gov",
                "old person",
                "192.0.2.2",
            },
        )

    @patch("{}.time.sleep".format(MODULE))
    @patch("{}.get_ident_group_info".format(MODULE))
    @patch("{}.create_ident_group".format(MODULE))
    @patch(
        "{}.check_ident_group_exists".format(MODULE),
        return_value=False,
    )
    @patch("{}.get_orgs".format(MODULE))
    def test_run_refresh_creates_missing_group(
        self,
        mock_get_orgs,
        mock_group_exists,
        mock_create_group,
        mock_get_group,
        mock_sleep,
    ):
        """A missing Flare group should be created before it is queried."""
        mock_get_orgs.return_value = [self.organizations[0]]
        mock_get_group.side_effect = RuntimeError("Stop after verifying group creation")

        with self.assertRaisesRegex(
            RuntimeError,
            "Stop after verifying group creation",
        ):
            run_flare_ident_refresh("B_ORG")

        mock_group_exists.assert_called_once_with("B_ORG")
        mock_create_group.assert_called_once_with("B_ORG")
        mock_get_group.assert_called_once_with("B_ORG")
        mock_sleep.assert_not_called()

    @patch("{}.time.sleep".format(MODULE))
    @patch(
        "{}.get_ident_group_info".format(MODULE),
        side_effect=RuntimeError("API failure"),
    )
    @patch(
        "{}.check_ident_group_exists".format(MODULE),
        return_value=True,
    )
    @patch("{}.get_orgs".format(MODULE))
    def test_run_refresh_stops_after_organization_failure(
        self,
        mock_get_orgs,
        mock_group_exists,
        mock_get_group,
        mock_sleep,
    ):
        """An organization failure should escape and stop further processing."""
        mock_get_orgs.return_value = [
            self.organizations[1],
            self.organizations[0],
        ]

        with self.assertRaisesRegex(RuntimeError, "API failure"):
            run_flare_ident_refresh("all")

        # Organizations are sorted by cyhy_db_name, so A_ORG fails first.
        mock_group_exists.assert_called_once_with("A_ORG")
        mock_get_group.assert_called_once_with("A_ORG")
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
