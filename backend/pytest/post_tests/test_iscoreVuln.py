#TODO
# POST/apiv1/iscore_vs_vuln
# GET/apiv1/iscore_vs_vuln/task/{task_id}
# POST/apiv1/iscore_vs_vuln_prev
# GET/apiv1/iscore_vs_vuln_prev/task/{task_id}
# POST/apiv1/iscore_pe_vuln
# GET/apiv1/iscore_pe_vuln/task/{task_id}

import os
from dotenv import load_dotenv
import unittest
import requests
import json

load_dotenv()

# Accessing variables
api_key = os.getenv('API_KEY')

headers = {"Content-Type": "application/json", "access_token": api_key}

org_uid = "c094fdf4-5d21-11ec-ac31-02589a36c9d7"

payload = {"specified_orgs": ["c094fdf4-5d21-11ec-ac31-02589a36c9d7"]}

class TestIscoreVsVuln(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/iscore_vs_vuln"
            response = requests.post(api_url, json=payload, headers=headers, verify=False)
            assert response.status_code == 200
            if response.status_code == 200:
                task_id = response.json()

                task_id = task_id['task_id']
            else:
                print("No task id found")
            # Optionally, add more checks for the response content

        except requests.exceptions.RequestException as e:
            return print(f"Endpoint failed - {e}")


        api_url = "http://127.0.0.1:8089/apiv1/iscore_vs_vuln/task/" + task_id
        response = requests.post(api_url, headers=headers,
                                 verify=False)

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
        with open("results/iscore_vs_vuln.json", 'r') as file:
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



class TestIscoreVsVulnPrev(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/iscore_vs_vuln_prev"
            response = requests.post(api_url, json=payload, headers=headers, verify=False)
            assert response.status_code == 200
            if response.status_code == 200:
                task_id = response.json()

                task_id = task_id['task_id']
            else:
                print("No task id found")
            # Optionally, add more checks for the response content

        except requests.exceptions.RequestException as e:
            return print(f"Endpoint failed - {e}")


        api_url = "http://127.0.0.1:8089/apiv1/iscore_vs_vuln_prev/task/" + task_id
        response = requests.post(api_url, headers=headers,
                                 verify=False)

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
        with open("results/iscore_vs_vuln_prev.json", 'r') as file:
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



class TestIscorePeVuln(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_vuln"
            response = requests.post(api_url, json=payload, headers=headers, verify=False)
            assert response.status_code == 200
            if response.status_code == 200:
                task_id = response.json()

                task_id = task_id['task_id']
            else:
                print("No task id found")
            # Optionally, add more checks for the response content

        except requests.exceptions.RequestException as e:
            return print(f"Endpoint failed - {e}")


        api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_vuln/task/" + task_id
        response = requests.post(api_url, headers=headers,
                                 verify=False)

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
        with open("results/iscore_pe_vuln.json", 'r') as file:
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