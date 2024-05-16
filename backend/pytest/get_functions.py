import requests
import json

def status_call_test(url_two, headers):
    # Headers or other necessary parameters
    api_url = "http://127.0.0.1:8089/apiv1/" + url_two

    try:

        # Making a GET request to the API
        response = requests.get(api_url, headers=headers, verify=False)

        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            return True
        else:
            return False
        # Optionally, add more checks for the response content

    except requests.exceptions.RequestException as e:
        return print(f"Endpoint failed - {e}")


def content_test(url, headers):
    api_url = "http://127.0.0.1:8089/apiv1/" + url

    try:

        # Making a GET request to the API
        response = requests.get(api_url, headers=headers, verify=False)

        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            return response.json
        else:
            return False
        # Optionally, add more checks for the response content

    except requests.exceptions.RequestException as e:
        return print(f"Endpoint failed - {e}")


def compare_json_with_file(url, headers, file_path, sort_key):
    """
    Compares JSON data from a request to a given URL with JSON data stored in a file.

    Parameters:
    - url (str): The URL to send the request to.
    - file_path (str): The path to the file containing JSON data to compare with.

    Returns:
    - bool: True if the JSON data match, False otherwise.
    """
    api_url = "http://127.0.0.1:8089/apiv1/" + url

    try:
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

        api_data = api_data.sort(key=lambda x: x[sort_key])

        #print(api_data[-100:])

        # Read the JSON data from the file
        with open(file_path, 'r') as file:
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
        #print(file_json[-100:])
        file_json = file_json.sort(key=lambda x: x[sort_key])

        # Compare the two JSON data sets
        return api_data == file_json

    except requests.RequestException as e:
        print(f"Request error: {e}")
        return False
    except json.JSONDecodeError:
        print("Error decoding JSON from the response or file.")
        return False
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
