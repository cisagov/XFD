# TODO:
#  Call /apiv1/orgs and verify that it comes back with right data
#  This is a large API endpoint so need to make sure that you do the status check and the json test at the same time

import os
from dotenv import load_dotenv
import unittest
import requests
import json

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

headers = {"Content-Type": "application/json", "access_token": api_key}

api_url = "http://127.0.0.1:8089/apiv1/orgs"


class TestOnline(unittest.TestCase):
    def test_compare_json_true(self):
        response = requests.post("http://127.0.0.1:8089/apiv1/subdomains/46cd2070-853d-11ec-9b71", headers=headers,
                                 verify=False)
        assert response.status_code == 500

        response = requests.post(api_url, headers=headers, verify=False)
        # Convert API Json to string and convert to lower
        api_data = response.json()
        api_data = json.dumps(api_data)
        api_data = api_data.lower()
        try:
            api_data = json.loads(api_data)
        except json.decoder.JSONDecodeError:
            print("Error: Modified string contains invalid JSON boolean values (TRUE/FALSE).")
            return None

        api_data = api_data.sort(key=lambda x: x["organizations_uid"])

        # Read the JSON data from the file
        with open("results/Get_orgs.json", 'r') as file:
            file_json = json.load(file)

        # Convert Json to string, convert to lower and strip \
        file_json = json.dumps(file_json)
        file_json = file_json.lower()
        file_json = file_json.replace("\\", "")

        try:
            file_json = json.loads(file_json)
        except json.decoder.JSONDecodeError:
            print("Error: Modified string contains invalid JSON boolean values (TRUE/FALSE).")
            return None
        file_json = file_json.sort(key=lambda x: x["organizations_uid"])
        assert api_data == file_json
        pass


if __name__ == '__main__':
    unittest.main()
