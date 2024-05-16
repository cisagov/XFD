# TODO:
#  Dont need to worry about this one
#  Call /apiv1/fetch_weekly_statuses and verify that it comes back with right data
#  Call /apiv1/fetch_user_weekly_statuses/ and verify that it comes back with right data <- needs to use body

import requests

data = {
    "user_fname": "string"
}

def get_org(headers):
    api_url = "http://127.0.0.1:8089/apiv1/orgs"

    try:

        # Making a GET request to the API
        response = requests.post(api_url, headers=headers, verify=False)

        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            print(
                f"Preflight Check Passed: Successfully connected to the /apiv1/orgs endpoint")
            data = response.json()
            # Verify Data
        else:
            print(f"Preflight Check Failed: returned status code {response.status_code}")

        # Optionally, add more checks for the response content

    except requests.exceptions.RequestException as e:
        print(f"Preflight Check Failed: An error occurred - {e}")
