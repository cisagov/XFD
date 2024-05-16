# TODO
#  POST/apiv1/cyhy_db_asset

import post_fuctions
import os
from dotenv import load_dotenv
import unittest

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

headers = {"Content-Type": "application/json", "access_token": api_key}

payload_true = {"org_id": "DHS_CISA"}
payload_false = {"org_id": "AAA"}


class TestOnline(unittest.TestCase):
    def test_online(self):
        # Call the endpoint and see if its online
        self.assertTrue(post_fuctions.status_call_test("cyhy_db_asset", payload_true, headers))

    def test_get_data(self):
        self.assertTrue(post_fuctions.content_test("cyhy_db_asset", payload_true, headers))

    def test_no_data(self):
        self.assertTrue(post_fuctions.negative_content_test("cyhy_db_asset", payload_false, headers))

    def test_compare_json_true(self):
        self.assertTrue(post_fuctions.compare_json_with_file("cyhy_db_asset", payload_true, headers,
                                                             "results/cyhyDbAsset.json", "network"))


if __name__ == '__main__':
    unittest.main()
