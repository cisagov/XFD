# TODO
#  POST/apiv1/orgs_attacksurface

import post_fuctions
import os
from dotenv import load_dotenv
import unittest

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

headers = {"Content-Type": "application/json", "access_token": api_key}

org_uid = "c094fdf4-5d21-11ec-ac31-02589a36c9d7"

payload_true = {"organizations_uid": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}
payload_false = {"organizations_uid": "3fa85f64"}


class TestOnline(unittest.TestCase):
    def test_online(self):
        # Call the endpoint and see if its online
        self.assertTrue(post_fuctions.status_call_test("orgs_attacksurface", payload_true, headers))

    def test_get_data(self):
        self.assertTrue(post_fuctions.content_test("orgs_attacksurface", payload_true, headers))

    def test_no_data(self):
        self.assertTrue(post_fuctions.negative_content_test("orgs_attacksurface", payload_false, headers))

    def test_compare_json_true(self):
        self.assertTrue(post_fuctions.compare_json_with_file("orgs_attacksurface", payload_true, headers,
                                                             "results/Org_attackSurface.json", "organizations_uid"))


if __name__ == '__main__':
    unittest.main()