"""Tests for Shodan API initialization."""

# Standard Python Libraries
import os
import unittest
from unittest.mock import MagicMock, patch

# Third-Party Libraries
from pe_source.data.config_source import shodan_api_init


class ShodanApiInitTests(unittest.TestCase):
    """Verify workers skip redundant api.info() validation."""

    @patch("pe_source.data.config_source.shodan.Shodan")
    def test_skips_api_info_when_key_assigned(self, mock_shodan):
        """Controller-assigned keys should not call api.info() in the worker."""
        client = MagicMock()
        mock_shodan.return_value = client

        with patch.dict(os.environ, {"PE_SHODAN_API_KEY": "secret-key"}, clear=False):
            apis = shodan_api_init()

        mock_shodan.assert_called_once_with("secret-key")
        client.info.assert_not_called()
        self.assertEqual(apis, [client])


if __name__ == "__main__":
    unittest.main()
