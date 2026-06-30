"""Unit tests for dnstwist scan helpers."""

# Standard Python Libraries
import os
import unittest
import uuid

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
from pe_source.dnstwist import checkBlocklist
from pe_source.dnstwist.dnstwist import _requested_org_names


class DnstwistOrgFilterTests(unittest.TestCase):
    """Verify explicit org filtering uses exact cyhy_db_name matches."""

    def test_single_org_does_not_match_substrings(self):
        """DHS_CISA must not match DHS, CIS, or other substring collisions."""
        requested = _requested_org_names("DHS_CISA")
        self.assertEqual(requested, {"DHS_CISA"})
        self.assertNotIn("DHS", requested)
        self.assertNotIn("CIS", requested)

    def test_comma_separated_orgs(self):
        """Comma-separated org lists should split into distinct names."""
        requested = _requested_org_names("DHS,DHS_CISA")
        self.assertEqual(requested, {"DHS", "DHS_CISA"})


class DnstwistBlocklistTests(unittest.TestCase):
    """Verify dnstwist blocklist helper edge cases."""

    def test_blocklist_row_includes_primary_key(self):
        """Each permutation row must include suspected_domain_uid for PE DB insert."""
        domain, perm_list = checkBlocklist(
            {
                "fuzzer": "bitsquatting",
                "domain": "examp1e.gov",
                "dns_a": ["1.2.3.4"],
            },
            "sub-uid",
            "source-uid",
            "org-uid",
            [],
        )
        self.assertIsNotNone(domain)
        self.assertIsNotNone(domain["suspected_domain_uid"])
        uuid.UUID(domain["suspected_domain_uid"])
        self.assertEqual(perm_list, ["examp1e.gov"])

    def test_original_fuzzer_is_skipped(self):
        """Original-fuzzer rows should not produce a domain dict."""
        domain, perm_list = checkBlocklist(
            {"fuzzer": "original", "domain": "example.gov"},
            "sub-uid",
            "source-uid",
            "org-uid",
            [],
        )
        self.assertIsNone(domain)
        self.assertEqual(perm_list, [])

    def test_servfail_is_skipped(self):
        """DNS ServFail responses should be skipped."""
        domain, perm_list = checkBlocklist(
            {"fuzzer": "bitsquatting", "domain": "examp1e.gov", "dns_a": ["!ServFail"]},
            "sub-uid",
            "source-uid",
            "org-uid",
            [],
        )
        self.assertIsNone(domain)
        self.assertEqual(perm_list, [])


if __name__ == "__main__":
    unittest.main()
