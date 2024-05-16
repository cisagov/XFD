#TODO
# POST/apiv1/get_cve


import os
from dotenv import load_dotenv
import unittest
import requests
import post_fuctions

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

headers = {"Content-Type": "application/json", "access_token": api_key}

cve = "CVE-2006-0625"

payload = {
  "cve_name": "CVE-2006-0625"
}


class TestIscorePeCreds(unittest.TestCase):
  def test_online(self):
    try:
      api_url = "http://127.0.0.1:8089/apiv1/get_cve"
      response = requests.post(api_url, json=payload, headers=headers, verify=False)
      assert response.status_code == 200
    except requests.exceptions.RequestException as e:
      return print(f"Endpoint failed - {e}")

    def test_compare_json_true(self):
        self.assertTrue(post_fuctions.compare_json_with_file("get_cve", payload, headers,
                                                             "results/GetCve.json", "cve_data"))