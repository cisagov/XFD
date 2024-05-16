import requests
import time


def preflight_check(url_two, headers):
    # Headers or other necessary parameters
    api_url = "http://127.0.0.1:8089/apiv1/" + url_two

    try:
        start_time = time.time()

        # Making a GET request to the API
        response = response = requests.post(api_url, headers=headers, verify=False)

        end_time = time.time()
        duration = end_time - start_time

        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            return print(
                f"Preflight Check Passed: Successfully connected to the {url_two} endpoint and took {duration:.1f} seconds")
        else:
            return print(f"Preflight Check Failed: " + url_two + " returned status code " + str(
                response.status_code) + " and took " + str(duration) + " seconds")

        # Optionally, add more checks for the response content

    except requests.exceptions.RequestException as e:
       return print(f"Preflight Check Failed: An error occurred - {e}")
