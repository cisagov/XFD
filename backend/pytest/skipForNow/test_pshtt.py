###On hold till fixed###
import requests

##Change url_two to
def test_pshtt(headers):
    # Headers or other necessary parameters
    api_url = "http://127.0.0.1:8089/apiv1//pshtt_unscanned_domains"

    try:
        # Making a GET request to the API
        response = response = requests.post(api_url, headers=headers, verify=False)

        # Check if the status code is 200 (OK)
        if response.status_code == 200:
            return print(response)
        else:
            return print(f"Endpoint not working")

        # Optionally, add more checks for the response content

    except requests.exceptions.RequestException as e:
       return print(f"Endpoint failed - {e}")

###Todo: add test that should not work and vaidate that it give correct error code###


###Todo: add test to test the /apiv1/pshtt_unscanned_domains/task/{task_id}

# Todo: add test to test /apiv1/pshtt_result_update_or_insert <- this is a PUT request.