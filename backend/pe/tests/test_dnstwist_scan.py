"""Unit tests for dnstwist scan helpers."""

# Standard Python Libraries
import os
import unittest

os.environ.setdefault("PE_DB_NAME", "pe")
os.environ.setdefault("PE_DB_USERNAME", "pe")
os.environ.setdefault("PE_DB_PASSWORD", "test")
os.environ.setdefault("PE_API_KEY", "test-key")

# Third-Party Libraries
from pe_source.dnstwistscript import checkBlocklist


class DnstwistBlocklistTests(unittest.TestCase):
    """Verify dnstwist blocklist helper edge cases."""

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
