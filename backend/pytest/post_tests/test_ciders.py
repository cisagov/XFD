# TODO
#  POST/apiv1/cidrs

import post_fuctions
import os
from dotenv import load_dotenv
import unittest

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

headers = {"Content-Type": "application/json", "access_token": api_key}


class TestOnline(unittest.TestCase):
    def test_positive(self):
        # Call the endpoint and see if its online
        self.assertTrue(post_fuctions.status_call_test("cidrs", headers))

    def test_compare_json_true(self):
        self.assertTrue(post_fuctions.compare_json_with_file("cidrs", headers,
                                                             "results/cider.json", "cidr_uid"))


if __name__ == '__main__':
    unittest.main()
