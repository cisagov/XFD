import requests
import json


# This function is used to check to see if a API endpoint is online and can be called from any test
def status_call_test(*args):
    api_url = "http://127.0.0.1:8089/apiv1/" + args[0]

    try:
        if len(args) == 3:
            url, json_data, headers = args
            response = requests.post(api_url, json=json_data, headers=headers, verify=False)
        elif len(args) == 2:
            url, headers = args
            response = requests.post(api_url, headers=headers, verify=False)
        else:
            print("Error: This function takes either three or four arguments")
        # Making a GET request to the API

        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            return True
        else:
            return False
        # Optionally, add more checks for the response content

    except requests.exceptions.RequestException as e:
        return print(f"Endpoint failed - {e}")


def content_test(*args):
    api_url = "http://127.0.0.1:8089/apiv1/" + args[0]

    try:
        if len(args) == 3:
            url, json_data, headers = args
            response = requests.post(api_url, json=json_data, headers=headers, verify=False)
        elif len(args) == 2:
            url, headers = args
            response = requests.post(api_url, headers=headers, verify=False)
        else:
            print("Error: This function takes either three or four arguments")
        # Making a GET request to the API

        data = response.json()

        # Check if the response contains data
        if data:  # Checks if data is not None or an empty dictionary/list
            if isinstance(data, dict) and data.keys():
                return True
            elif isinstance(data, list) and len(data) > 0:
                return True
            else:
                return False
        else:
            return False


    except requests.exceptions.RequestException as e:
        return print(f"Endpoint failed - {e}")


# This function is designed to take in a imput and make sure we do not get back data if given a org that doesnt exist
# Need to add compair function to make sure it give back empty json

def negative_content_test(*args):
    api_url = "http://127.0.0.1:8089/apiv1/" + args[0]

    try:
        if len(args) == 3:
            url, json_data, headers = args
            response = requests.post(api_url, json=json_data, headers=headers, verify=False)
        elif len(args) == 2:
            url, headers = args
            response = requests.post(api_url, headers=headers, verify=False)
        else:
            print("Error: This function takes either three or four arguments")
        # Making a GET request to the API
        data = response.json()
        # Check if the response.json has data in it
        if not data:
            return True
        else:
            return False
        # Optionally, add more checks for the response content

    except requests.exceptions.RequestException as e:
        return print(f"Endpoint failed - {e}")


# This function takes the return from a API call and compairs it to the known data we have. Can be used to tell if
# data is returnd correctorly
def compare_json_with_file(*args):
    """
    Compares JSON data from a request to a given URL with JSON data stored in a file.

    Parameters:
    - url (str): The URL to send the request to.
    - file_path (str): The path to the file containing JSON data to compare with.

    Returns:
    - bool: True if the JSON data match, False otherwise.
    """
    api_url = "http://127.0.0.1:8089/apiv1/" + args[0]

    try:
        if len(args) == 5:
            url, json_data, headers, file_path, sort_key = args
            response = requests.post(api_url, json=json_data, headers=headers, verify=False)
        elif len(args) == 4:
            url, headers, file_path, sort_key = args
            response = requests.post(api_url, headers=headers, verify=False)
        else:
            print("Error: This function takes either three or four arguments")

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


# Fuction is used to write data returned from API Call to file. Mostly used for initial data baseline testing
def write_data(*args):
    api_url = "http://127.0.0.1:8089/apiv1/" + args[0]

    try:
        if len(args) == 4:
            url, json_data, headers, filepath = args
            print(json_data)
            response = requests.post(api_url, json=json_data, headers=headers, verify=False)
            print(response)
        elif len(args) == 3:
            url, headers, filepath = args
            response = requests.post(api_url, headers=headers, verify=False)
        else:
            print("Error: This function takes either three or four arguments")
        # Parse JSON
        data = response.json()

        # Save to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    except requests.RequestException as e:
        print("HTTP Request failed: ", e)
    except json.JSONDecodeError:
        print("Error decoding JSON")
    except Exception as e:
        print("An error occurred: ", e)
