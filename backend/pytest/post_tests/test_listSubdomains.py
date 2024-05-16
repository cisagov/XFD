# TODO:
#  Need to call /apiv1/subdomains/{root_domain_uid} and validate the response is correct
#  Need to call /apiv1/subdomains/{root_domain_uid} with false data to test if end point handles error correction
#  Use CISA as test org_uid = c094fdf4-5d21-11ec-ac31-02589a36c9d7
#  Use root_domain_uid = 46cd2070-853d-11ec-9b71-02589a36c9d7


import post_fuctions
import os
from dotenv import load_dotenv
import unittest
import requests

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

# headers = {"Authorization": f"Bearer {api_key}"}


headers = {"Content-Type": "application/json", "access_token": api_key}

root_domain_uid = "46cd2070-853d-11ec-9b71-02589a36c9d7"


class TestOnline(unittest.TestCase):
    def test_online(self):
        # Call the endpoint and see if its online
        self.assertTrue(post_fuctions.status_call_test("subdomains/46cd2070-853d-11ec-9b71-02589a36c9d7", headers))

    def test_get_data(self):
        #Call to see if you get data back for a correct org
        self.assertTrue(post_fuctions.content_test("subdomains/46cd2070-853d-11ec-9b71-02589a36c9d7", headers))

    def test_for_wrong_UID(self):
        # This is to test that when given a wrong UID it gives the correct error handling (In this endpoint it throws a 500 error code)
        #self.assertTrue(post_fuctions.negative_content_test("subdomains/46cd2070-853d-11ec-9b71-02589a36c9d7", headers))
        response = requests.post("http://127.0.0.1:8089/apiv1/subdomains/46cd2070-853d-11ec-9b71", headers=headers, verify=False)
        assert response.status_code == 500
        pass

    def test_compare_json_true(self):
        self.assertTrue(post_fuctions.compare_json_with_file("subdomains/46cd2070-853d-11ec-9b71-02589a36c9d7", headers, "results/lstSubdomain.json","sub_domain_uid"))


if __name__ == '__main__':
    unittest.main()
