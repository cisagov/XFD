# TODO
# POST/apiv1/iscore_pe_cred
# GET/apiv1/iscore_pe_cred/task/{task_id}
# POST/apiv1/iscore_pe_breach
# GET/apiv1/iscore_pe_breach/task/{task_id}
# POST/apiv1/iscore_pe_darkweb
# GET/apiv1/iscore_pe_darkweb/task/{task_id}
# POST/apiv1/iscore_pe_protocol
# GET/apiv1/iscore_pe_protocol/task/{task_id}

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

payload = {"specified_orgs": ["c094fdf4-5d21-11ec-ac31-02589a36c9d7"],
           "start_date": "2024-01-01",
           "end_date": "2024-01-15"
           }


class TestIscorePeCreds(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_cred"
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

        api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_cred/task/" + task_id
        response = requests.get(api_url, headers=headers,
                                verify=False)

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
        with open("results/dscore_pe_ip.json", 'r') as file:
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


class TestIscorePeBreach(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_breach"
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

        api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_breach/task/" + task_id
        response = requests.get(api_url, headers=headers,
                                verify=False)

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
        with open("results/dscore_pe_ip.json", 'r') as file:
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


class TestIscorePeDarkweb(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_darkweb"
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

        api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_darkweb/task/" + task_id
        response = requests.get(api_url, headers=headers,
                                verify=False)

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
        with open("results/dscore_pe_ip.json", 'r') as file:
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


class TestIscorePeProtocol(unittest.TestCase):
    def test_online(self):
        try:
            api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_protocol"
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

        api_url = "http://127.0.0.1:8089/apiv1/iscore_pe_protocol/task/" + task_id
        response = requests.get(api_url, headers=headers,
                                verify=False)

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
        with open("results/dscore_pe_ip.json", 'r') as file:
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
