# TODO
#  POST/apiv1/ve_info
#  GET/apiv1/ve_info/task/{task_id}

import os
from dotenv import load_dotenv
import unittest
import requests
import json

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

headers = {"Content-Type": "application/json", "access_token": api_key}


class TestVeInfo(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/ve_info"
            response = requests.post(api_url, headers=headers, verify=False)
            assert response.status_code == 200
            if response.status_code == 200:
                task_id = response.json()
                task_id = task_id['task_id']
            else:
                print("No task id found")
            # Optionally, add more checks for the response content

        except requests.exceptions.RequestException as e:
            return print(f"Endpoint failed - {e}")

        api_url = "http://127.0.0.1:8089/apiv1/ve_info/task" + task_id

        response = requests.get(api_url, headers=headers, verify=False)

        # Convert API Json to string and convert to lower
        api_data = response.json()
        api_data = json.dumps(api_data)
        api_data = api_data.lower()
        try:
            api_data = json.loads(api_data)
        except json.decoder.JSONDecodeError:
            print("Error: Modified string contains invalid JSON boolean values (TRUE/FALSE).")
            return None

        api_data = api_data.sort(key=lambda x: x["task_id"])

        # Read the JSON data from the file
        with open("results/ve_info", 'r') as file:
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
        file_json = file_json.sort(key=lambda x: x["task_id"])
        assert api_data == file_json
        pass


if __name__ == '__main__':
    unittest.main()
