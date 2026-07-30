"""Tests for keyed-scan worker planning."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import patch

# Third-Party Libraries
from pe.worker_key_planner import (
    KEYED_SCANS,
    api_key_label,
    plan_worker_keys,
    worker_key_env,
)


class ApiKeyLabelTests(unittest.TestCase):
    """Verify masked API key labels for logs."""

    def test_masks_long_keys(self):
        """Long keys should log only the last four characters."""
        self.assertEqual(api_key_label("abcdefghijklmnop"), "...mnop")

    def test_short_keys_are_fully_masked(self):
        """Short keys should not be logged verbatim."""
        self.assertEqual(api_key_label("abc"), "****")


class PlanWorkerKeysTests(unittest.TestCase):
    """Verify load / validate / clamp for keyed scans."""

    @patch.dict(
        "pe.worker_key_planner.KEYED_SCANS",
        {
            "flare_events": {
                "keys_env": "FLARE_API_KEYS",
                "worker_env": "FLARE_API_KEY",
                "validate": lambda keys: keys,
            },
            "flare_creds": {
                "keys_env": "FLARE_API_KEYS",
                "worker_env": "FLARE_API_KEY",
                "validate": lambda keys: keys,
            },
            "shodan": {
                "keys_env": "PE_SHODAN_API_KEYS",
                "worker_env": "PE_SHODAN_API_KEY",
                "validate": lambda keys: keys,
            },
        },
        clear=False,
    )
    def test_count_higher_than_keys_caps(self):
        """Requested count above valid keys starts one container per key."""
        with patch.dict(os.environ, {"FLARE_API_KEYS": "k1,k2"}, clear=False):
            self.assertEqual(plan_worker_keys("flare_events", 5), ["k1", "k2"])
            self.assertEqual(plan_worker_keys("flare_creds", 5), ["k1", "k2"])
        with patch.dict(os.environ, {"PE_SHODAN_API_KEYS": "k1,k2"}, clear=False):
            self.assertEqual(plan_worker_keys("shodan", 5), ["k1", "k2"])

    @patch.dict(
        "pe.worker_key_planner.KEYED_SCANS",
        {
            "shodan": {
                "keys_env": "PE_SHODAN_API_KEYS",
                "worker_env": "PE_SHODAN_API_KEY",
                "validate": lambda keys: keys,
            }
        },
        clear=False,
    )
    def test_count_lower_than_keys_uses_requested(self):
        """Requested count below valid keys uses only that many."""
        with patch.dict(os.environ, {"PE_SHODAN_API_KEYS": "k1,k2,k3"}, clear=False):
            self.assertEqual(plan_worker_keys("shodan", 2), ["k1", "k2"])

    @patch.dict(
        "pe.worker_key_planner.KEYED_SCANS",
        {
            "flare_events": {
                "keys_env": "FLARE_API_KEYS",
                "worker_env": "FLARE_API_KEY",
                "validate": lambda keys: [],
            },
            "flare_creds": {
                "keys_env": "FLARE_API_KEYS",
                "worker_env": "FLARE_API_KEY",
                "validate": lambda keys: [],
            },
            "shodan": {
                "keys_env": "PE_SHODAN_API_KEYS",
                "worker_env": "PE_SHODAN_API_KEY",
                "validate": lambda keys: [],
            },
        },
        clear=False,
    )
    def test_no_valid_keys_raises(self):
        """Zero valid keys should raise ValueError."""
        with patch.dict(os.environ, {"FLARE_API_KEYS": "bad"}, clear=False):
            with self.assertRaises(ValueError):
                plan_worker_keys("flare_events", 1)
                plan_worker_keys("flare_creds", 1)
        with patch.dict(os.environ, {"PE_SHODAN_API_KEYS": "bad"}, clear=False):
            with self.assertRaises(ValueError):
                plan_worker_keys("shodan", 1)

    @patch.dict(
        "pe.worker_key_planner.KEYED_SCANS",
        {
            "flare_events": {
                "keys_env": "FLARE_API_KEYS",
                "worker_env": "FLARE_API_KEY",
                "validate": lambda keys: keys[:3],
            },
            "flare_creds": {
                "keys_env": "FLARE_API_KEYS",
                "worker_env": "FLARE_API_KEY",
                "validate": lambda keys: keys[:3],
            },
            "shodan": {
                "keys_env": "PE_SHODAN_API_KEYS",
                "worker_env": "PE_SHODAN_API_KEY",
                "validate": lambda keys: keys[:3],
            },
        },
        clear=False,
    )
    def test_empty_env_raises(self):
        """Empty keys env var should raise before validation."""
        with patch.dict(os.environ, {"FLARE_API_KEYS": ""}, clear=False):
            with self.assertRaises(ValueError):
                plan_worker_keys("flare_events", 2)
                plan_worker_keys("flare_creds", 2)
        with patch.dict(os.environ, {"PE_SHODAN_API_KEYS": ""}, clear=False):
            with self.assertRaises(ValueError):
                plan_worker_keys("shodan", 2)


class WorkerKeyEnvTests(unittest.TestCase):
    """Verify per-worker env injection."""

    def test_flare_includes_tenant(self):
        """Flare workers get FLARE_API_KEY and FLARE_TENANT_ID."""
        with patch.dict(os.environ, {"FLARE_TENANT_ID": "123"}, clear=False):
            env = worker_key_env("flare_events", "secret")
        self.assertEqual(env["FLARE_API_KEY"], "secret")
        self.assertEqual(env["FLARE_TENANT_ID"], "123")

    def test_shodan_singular_key(self):
        """Shodan workers get PE_SHODAN_API_KEY only."""
        env = worker_key_env("shodan", "secret")
        self.assertEqual(env, {"PE_SHODAN_API_KEY": "secret"})


class RegistryTests(unittest.TestCase):
    """Verify keyed scan registry."""

    def test_flare_and_shodan_registered(self):
        """Flare and Shodan scans should be in KEYED_SCANS."""
        self.assertIn("flare_events", KEYED_SCANS)
        self.assertIn("flare_creds", KEYED_SCANS)

    def test_shodan_scans_registered(self):
        """Shodan scans should be in KEYED_SCANS."""
        self.assertIn("shodan", KEYED_SCANS)
        self.assertIn("asmSync", KEYED_SCANS)


if __name__ == "__main__":
    unittest.main()
