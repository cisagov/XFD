"""Regression Tests for Users Endpoint."""

# Standard Python Libraries
import os
import uuid

# Third-Party Libraries
import pytest
import requests

# ——— Configuration ———
BASE_URL = os.environ.get("BACKEND_DOMAIN")
X_API_KEY = os.environ.get("X_API_KEY")
HEADERS = {"X-API-KEY": X_API_KEY}
BAD_HEADERS = {"X-API-KEY": "invalid-key"}
BAD_ID = "00000000-0000-0000-0000-000000000000"
INVALID = "cisa"
TIMEOUT = 10
ROLE_MEMBER = "member"


@pytest.fixture(scope="session")
def all_organizations():
    """Fetch the full list of organizations once per test session."""
    url = f"{BASE_URL}/organizations"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"/organizations returned {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list) and data, "Expected a non-empty list of organizations"
    return data


@pytest.fixture(scope="session")
def sample_org(all_organizations):
    """Pick one organization from the list for downstream tests."""
    return all_organizations[0]


@pytest.fixture(scope="session")
def all_users():
    """Fetch the full list of users once per test session."""
    url = f"{BASE_URL}/users"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"/users returned {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list) and data, "Expected a non-empty list of users"
    return data


@pytest.fixture(scope="session")
def sample_user(all_users):
    """Pick one organization from the list for downstream tests."""
    return all_users[0]


@pytest.fixture(scope="session")
def user_id(sample_user):
    """Retrieve organization id from sample org."""
    return sample_user["id"]


@pytest.fixture(scope="session")
def region_id(sample_user):
    """Retrieve region id from sample org."""
    return sample_user.get("region_id")


@pytest.fixture(scope="session")
def state(sample_user):
    """Retrieve state from sample org."""
    return sample_user.get("state")


@pytest.fixture(scope="function")
def test_user():
    """Creates a temporary user via POST /users.

    Yields the new user record, then deletes it after the test.
    """
    email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": email,
        "region_id": "3",
        "state": "Virginia",
        "user_type": "standard",
    }

    resp = requests.post(
        f"{BASE_URL}/users",
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"User invite failed: {resp.status_code}"
    user = resp.json()

    yield user

    # teardown: delete the user
    del_url = f"{BASE_URL}/users/{user['id']}"
    try:
        del_resp = requests.delete(
            del_url,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        assert del_resp.status_code in (
            200,
            404,
        ), f"Cleanup DELETE failed: {del_resp.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Could not clean up test user due to request error: {e}")


# ========================================
#   Assert failures for endpoints
# ========================================


def assert_auth_failure(resp, context=""):
    """Assert that a response indicates an authentication failure (401 or 403)."""
    assert resp.status_code in (401, 403), (
        f"{context}Expected 401 or 403, got {resp.status_code}. "
        f"Response body: {resp.text}"
    )
    detail = resp.json().get("detail", "")
    assert isinstance(
        detail, str
    ), f"{context}Expected 'detail' as string, got {type(detail)}"


# Centralized test
@pytest.mark.integration
@pytest.mark.parametrize("headers", [None, BAD_HEADERS], ids=["no-auth", "bad-auth"])
@pytest.mark.parametrize(
    "method, endpoint_template",
    [
        ("POST", "/users/me/acceptTerms"),
        ("GET", "/users/me"),
        ("DELETE", "/users/{user_id}"),
        ("GET", "/users"),
        ("GET", "/users/region_id/{region_id}"),
        ("GET", "/users/state/{state}"),
        ("GET", "/v2/users"),
        ("PUT", "/v2/users/{user_id}"),
        ("PUT", "/users/{user_id}/register/approve"),
        ("PUT", "/users/{user_id}/register/deny"),
        ("POST", "/users"),
    ],
)
def test_auth_failure_single_request(
    headers, method, endpoint_template, test_user, region_id, state
):
    """Each (method, URL, auth header) pair is its own test."""
    url = f"{BASE_URL}" + endpoint_template.format(
        user_id=test_user["id"], region_id=region_id, state=state
    )
    resp = requests.request(method, url, headers=headers, timeout=TIMEOUT)
    context = f"[{method} {url}] "
    assert_auth_failure(resp, context)


@pytest.mark.integration
@pytest.mark.parametrize(
    "method, endpoint_template",
    [
        ("GET", "/users/me/acceptTerms"),
        ("POST", "/users/me"),
        ("GET", "/users/{user_id}"),
        ("POST", "/users/region_id/{region_id}"),
        ("POST", "/users/state/{state}"),
        ("POST", "/v2/users"),
        ("GET", "/v2/users/{user_id}"),
        ("GET", "/users/{user_id}/register/approve"),
        ("GET", "/users/{user_id}/register/deny"),
    ],
)
def test_methods_not_allowed(method, endpoint_template, test_user, region_id, state):
    """Ensure that unsupported methods return 405 with real IDs."""
    url = f"{BASE_URL}" + endpoint_template.format(
        user_id=test_user["id"], region_id=region_id, state=state
    )

    resp = requests.request(method, url, headers=HEADERS, timeout=TIMEOUT)
    assert (
        resp.status_code == 405
    ), f"[{method} {url}] Expected 405, got {resp.status_code}"


# =======================================
#   POST users/acceptTerms
# =======================================


@pytest.fixture(scope="function")
def original_terms_state():
    """Save the current user's accepted_terms_version and then restore them after test."""
    me_resp = requests.get(f"{BASE_URL}/users/me", headers=HEADERS, timeout=TIMEOUT)
    assert me_resp.status_code == 200
    me = me_resp.json()
    orig_version = me.get("accepted_terms_version")
    orig_date = me.get("date_accepted_terms")
    yield orig_version, orig_date

    # Teardown: restore the original version if it existed
    if orig_version:
        requests.post(
            f"{BASE_URL}/users/me/acceptTerms",
            json={"version": orig_version},
            headers=HEADERS,
            timeout=TIMEOUT,
        )


@pytest.mark.integration
def test_accept_terms_success(original_terms_state):
    """POST /users/me/acceptTerms with a valid version should return 200 and update the fields."""
    new_version = "Test-Version"
    resp = requests.post(
        f"{BASE_URL}/users/me/acceptTerms",
        json={"version": new_version},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    user = resp.json()
    assert user["accepted_terms_version"] == new_version
    assert user["date_accepted_terms"] is not None


@pytest.mark.integration
def test_accept_terms_missing_version():
    """POST without 'version' should return 422 Unprocessable Entity due to request validation."""
    resp = requests.post(
        f"{BASE_URL}/users/me/acceptTerms",
        json={},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert (
        resp.status_code == 422
    ), f"Expected 422 Unprocessable Entity, got {resp.status_code}"
    err = resp.json()
    assert isinstance(err.get("detail"), list), f"Expected 'detail' list, got: {err}"


@pytest.mark.integration
def test_accept_terms_empty_version():
    """POST with {"version": ""} will raises a 500."""
    resp = requests.post(
        f"{BASE_URL}/users/me/acceptTerms",
        json={"version": ""},
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert (
        resp.status_code == 500
    ), f"Expected 500 Internal Server Error, got {resp.status_code}"
    err = resp.json()
    assert "Missing version in request body." in err.get(
        "detail", ""
    ), f"Unexpected detail: {err}"


# ========================================
#   GET users/me
# ========================================


@pytest.mark.integration
def test_read_users_me_success():
    """GET /users/me should return 200 and the current user's info."""
    url = f"{BASE_URL}/users/me"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = resp.json()
    # Basic shape checks
    assert isinstance(data, dict), "Response body should be a JSON object"
    assert "id" in data and isinstance(data["id"], str), "Missing or invalid 'id'"
    assert "email" in data and "@" in data["email"], "Missing or invalid 'email'"


# ========================================
#   DELETE users/user_id
# ========================================


@pytest.mark.integration
def test_delete_user_success(test_user):
    """
    DELETE /users/{user_id}.

    - returns 200
    - returns a JSON body indicating the user was removed
    - subsequent GET /users/{user_id} returns 404 or 405
    """
    user_id = test_user["id"]
    url = f"{BASE_URL}/users/{user_id}"

    # delete
    resp = requests.delete(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = resp.json()
    assert isinstance(data, dict), "Response body should be a JSON object"

    # the response_model returns a status + message on successful deletion
    assert (
        data.get("status", "").lower() == "success"
    ), f"Unexpected status: {data.get('status')}"
    assert f"User {user_id}" in data.get(
        "message", ""
    ), f"Expected confirmation message to reference user {user_id}, got: {data.get('message')}"

    # verify the user is no longer accessible
    get_resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert get_resp.status_code in (
        404,
        405,
    ), f"Expected 404 Not Found or 405 Method Not Allowed, got {get_resp.status_code}"


@pytest.mark.integration
def test_delete_nonexistent_user_returns_404():
    """
    DELETE /users/{random-uuid} for a user that doesn’t exist.

    should return 404 Not Found.
    """
    url = f"{BASE_URL}/users/{BAD_ID}"
    resp = requests.delete(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"


@pytest.mark.integration
def test_delete_invalid():
    """DELETE /users/ for a user that doesn’t exist should return 405 Not Found."""
    url = f"{BASE_URL}/users/"
    resp = requests.delete(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 405, f"Expected 405 Not Found, got {resp.status_code}"


# ========================================
#   GET users
# ========================================


@pytest.mark.integration
def test_get_users_success():
    """
    GET /users should return 200 and a list of users.

    Each item must include at least 'id' and 'email'.
    """
    url = f"{BASE_URL}/users"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list), f"Expected JSON list, got {type(users).__name__}"
    assert len(users) > 0, "Expected at least one user in the list"
    for u in users:
        assert isinstance(u, dict), "Each user must be a JSON object"
        assert "id" in u and isinstance(u["id"], str), "Missing or invalid 'id'"
        assert "email" in u and isinstance(
            u["email"], str
        ), "Missing or invalid 'email'"


# ========================================
#   GET users region_id
# ========================================


@pytest.mark.integration
def test_get_users_by_region_success(region_id):
    """
    GET /users/region_id/{region_id} should return 200 and a list of users.

    where each user's region_id matches the requested region_id.
    """
    url = f"{BASE_URL}/users/region_id/{region_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list), f"Expected JSON list, got {type(users).__name__}"
    assert len(users) > 0, "Expected at least one user in this region"
    for u in users:
        assert isinstance(u, dict), "Each user must be a JSON object"
        assert (
            u.get("region_id") == region_id
        ), f"Expected region_id {region_id}, got {u.get('region_id')}"
        # shape checks
        assert "id" in u and isinstance(u["id"], str), "Missing or invalid 'id'"
        assert "email" in u and isinstance(
            u["email"], str
        ), "Missing or invalid 'email'"


@pytest.mark.integration
def test_get_users_by_nonexistent_region_returns_404():
    """
    GET /users/region_id/{random_uuid} for a region with no users.

    should return 404 Not Found.
    """
    url = f"{BASE_URL}/users/region_id/12345"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert isinstance(err, dict), "Error response should be a JSON object"
    assert "detail" in err, "Error response should include a 'detail' message"


@pytest.mark.integration
def test_get_users_by_invalid_region_returns_404():
    """GET /users/region_id/{invalid_string} should return 404 Not Found."""
    url = f"{BASE_URL}/users/region_id/cisa"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert isinstance(err, dict), "Error response should be a JSON object"
    assert "detail" in err, "Error response should include a 'detail' message"


# ========================================
#   GET users state
# ========================================


@pytest.mark.integration
def test_get_users_by_state_success(state):
    """
    GET /users/state/{state}.

    should return 200 and a list of users whose 'state' matches the requested value.
    """
    url = f"{BASE_URL}/users/state/{state}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list), f"Expected JSON list, got {type(users).__name__}"
    assert len(users) > 0, "Expected at least one user in this state"
    for u in users:
        assert isinstance(u, dict), "Each user must be a JSON object"
        assert (
            u.get("state") == state
        ), f"Expected state '{state}', got '{u.get('state')}'"
        assert "id" in u and isinstance(u["id"], str), "Missing or invalid 'id'"
        assert "email" in u and isinstance(
            u["email"], str
        ), "Missing or invalid 'email'"


@pytest.mark.integration
def test_get_users_by_nonexistent_state_returns_404():
    """GET /users/state/{nonexistent} should return 404 Not Found."""
    url = f"{BASE_URL}/users/state/Atlantis"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert isinstance(err, dict), "Error response should be a JSON object"
    assert "detail" in err, "Error response should include a 'detail' message"


@pytest.mark.integration
def test_get_users_by_number_state_returns_404():
    """GET /users/state/{nonexistent} should return 404 Not Found."""
    url = f"{BASE_URL}/users/state/12345"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert isinstance(err, dict), "Error response should be a JSON object"
    assert "detail" in err, "Error response should include a 'detail' message"


# ========================================
#   GET v2 users
# ========================================


REQUIRED_KEYS = [
    "id",
    "created_at",
    "updated_at",
    "first_name",
    "last_name",
    "full_name",
    "email",
    "region_id",
    "state",
    "user_type",
    "roles",
    "can_select_own_state",
]


@pytest.mark.integration
def test_get_users_v2_no_filters():
    """GET /v2/users should return 200 and at least one user."""
    url = f"{BASE_URL}/v2/users"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list), f"Expected list, got {type(users).__name__}"
    assert users, "Expected at least one user"
    for u in users:
        assert isinstance(u, dict)
        for key in REQUIRED_KEYS:
            assert key in u, f"Missing key '{key}' in user object"


@pytest.mark.integration
def test_get_users_v2_filter_by_state(state):
    """GET /v2/users?state={state} should return 200 and only users in that state."""
    url = f"{BASE_URL}/v2/users?state={state}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list)
    assert users, "Expected at least one user for this state"
    for u in users:
        assert (
            u.get("state") == state
        ), f"Expected state '{state}', got '{u.get('state')}'"


@pytest.mark.integration
def test_get_users_v2_filter_by_region(region_id):
    """GET /v2/users?region_id={region_id} should return 200 and only users in that region."""
    url = f"{BASE_URL}/v2/users?region_id={region_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list)
    assert users, "Expected at least one user for this region"
    for u in users:
        assert (
            u.get("region_id") == region_id
        ), f"Expected region_id '{region_id}', got '{u.get('region_id')}'"


@pytest.mark.integration
def test_get_users_v2_filter_by_invite_pending_false():
    """GET /v2/users?invite_pending=false should return 200 and a list of users."""
    url = f"{BASE_URL}/v2/users?invite_pending=false"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list), f"Expected list, got {type(users).__name__}"


@pytest.mark.integration
def test_get_users_v2_combined_filters(state, region_id):
    """
    GET /v2/users?state={state}&region_id={region_id}&invite_pending=false.

    should return 200 and only users matching both state and region.
    """
    url = (
        f"{BASE_URL}/v2/users?state={state}&region_id={region_id}&invite_pending=false"
    )
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list)
    for u in users:
        assert (
            u.get("state") == state
        ), f"Expected state '{state}', got '{u.get('state')}'"
        assert (
            u.get("region_id") == region_id
        ), f"Expected region_id '{region_id}', got '{u.get('region_id')}'"


@pytest.mark.integration
def test_get_users_v2_invalid_state_returns_empty_list():
    """GET /v2/users?state=ZZZ (non‑existent state) should return 200 and an empty list."""
    url = f"{BASE_URL}/v2/users?state=ZZZ"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list)
    assert users == [], f"Expected empty list for invalid state, got {users}"


@pytest.mark.integration
def test_get_users_v2_invalid_region_id_returns_empty_list():
    """
    GET /v2/users?region_id=00000000-0000-0000-0000-000000000000.

    should return 200 and an empty list.
    """
    bad_id = "00000000-0000-0000-0000-000000000000"
    url = f"{BASE_URL}/v2/users?region_id={bad_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    users = resp.json()
    assert isinstance(users, list)
    assert users == [], f"Expected empty list for invalid region_id, got {users}"


@pytest.mark.integration
def test_get_users_v2_invalid_invite_pending_returns_422():
    """GET /v2/users?invite_pending=notabool should return 422 Unprocessable Entity."""
    url = f"{BASE_URL}/v2/users?invite_pending=notabool"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert (
        resp.status_code == 422
    ), f"Expected 422 validation error, got {resp.status_code}"
    err = resp.json()
    assert "detail" in err, "Expected validation details in response"


# ========================================
#   PUT v2 users
# ========================================


@pytest.mark.integration
def test_update_user_v2_success(test_user):
    """
    PUT /v2/users/{user_id}.

    - returns 200
    - updates only the provided field(s)
    - returns the updated UserResponseV2
    """
    user_id = test_user["id"]
    new_first = "UpdatedFirst"
    url = f"{BASE_URL}/v2/users/{user_id}"
    payload = {"first_name": new_first}

    resp = requests.put(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"

    data = resp.json()
    assert data["id"] == user_id
    assert data["first_name"] == new_first
    assert data["full_name"] == f"{new_first} {data['last_name']}"


@pytest.mark.integration
def test_update_user_v2_not_found_invalid_uuid():
    """PUT /v2/users/{bad-uuid} should return 404 for malformed UUID."""
    url = f"{BASE_URL}/v2/users/{INVALID}"
    resp = requests.put(url, json={"first_name": "X"}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"


@pytest.mark.integration
def test_update_user_v2_not_found_nonexistent_uuid():
    """PUT /v2/users/{random-uuid} should return 404 when the user doesn't exist."""
    url = f"{BASE_URL}/v2/users/{BAD_ID}"
    resp = requests.put(url, json={"first_name": "X"}, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"


@pytest.mark.integration
def test_update_user_v2_email_update_forbidden(test_user):
    """
    PUT /v2/users/{user_id} attempting to change email.

    when not allowed should return 403 with an unauthorized-fields message.
    """
    user_id = test_user["id"]
    url = f"{BASE_URL}/v2/users/{user_id}"
    payload = {"email": "newemail@example.com"}

    resp = requests.put(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}"
    err = resp.json()
    detail = err.get("detail", "")
    assert "Unauthorized to update the following fields" in detail
    assert "email" in detail


@pytest.mark.integration
def test_update_user_v2_change_user_type_by_admin(test_user):
    """PUT /v2/users/{user_id} changing user_type should succeed for a global‑admin key."""
    user_id = test_user["id"]
    url = f"{BASE_URL}/v2/users/{user_id}"
    new_type = "globalAdmin" if test_user["user_type"] != "globalAdmin" else "standard"
    payload = {"user_type": new_type}

    resp = requests.put(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = resp.json()
    assert (
        data["user_type"] == new_type
    ), f"Expected user_type={new_type}, got {data['user_type']}"


# =======================================
#   PUT v2 users/user_id/register/approve
# =======================================


@pytest.fixture(scope="session")
def current_user_id():
    """Fetch the ID of the user associated with X_API_KEY."""
    resp = requests.get(f"{BASE_URL}/users/me", headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.integration
def test_register_approve_success(test_user):
    """
    PUT /users/{user_id}/register/approve.

    - returns 200
    - returns RegisterUserResponse with status_code and body
    """
    user_id = test_user["id"]
    url = f"{BASE_URL}/users/{user_id}/register/approve"

    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("status_code") == 200
    assert data.get("body") == "User registration approved."


@pytest.mark.integration
def test_register_approve_invalid_uuid():
    """
    PUT /users/not-a-uuid/register/approve.

    should return 404 with detail 'Invalid user ID.'
    """
    url = f"{BASE_URL}/users/not-a-uuid/register/approve"
    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert err.get("detail") == "Invalid user ID."


@pytest.mark.integration
def test_register_approve_user_not_found():
    """PUT /users/{random_uuid}/register/approve should return 404 with detail 'User not found.'."""
    random_id = str(uuid.uuid4())
    url = f"{BASE_URL}/users/{random_id}/register/approve"
    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert err.get("detail") == "User not found."


@pytest.mark.integration
def test_register_approve_self_forbidden(current_user_id):
    """
    PUT /users/{me}/register/approve.

    should return 403 with detail 'Users cannot approve themselves.'
    """
    url = f"{BASE_URL}/users/{current_user_id}/register/approve"
    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}"
    err = resp.json()
    assert err.get("detail") == "Users cannot approve themselves."


# =======================================
#   PUT v2 users/user_id/register/deny
# =======================================


@pytest.mark.integration
def test_register_deny_success(test_user):
    """
    PUT /users/{user_id}/register/deny.

    - returns 200
    - returns RegisterUserResponse with status_code and body
    """
    user_id = test_user["id"]
    url = f"{BASE_URL}/users/{user_id}/register/deny"

    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = resp.json()
    assert data.get("status_code") == 200
    assert data.get("body") == "User registration denied."


@pytest.mark.integration
def test_register_deny_invalid_uuid():
    """PUT /users/not-a-uuid/register/deny should return 404 with detail 'User not found.'."""
    url = f"{BASE_URL}/users/not-a-uuid/register/deny"
    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert err.get("detail") == "User not found."


@pytest.mark.integration
def test_register_deny_user_not_found():
    """PUT /users/{random_uuid}/register/deny should return 404 with detail 'User not found.'."""
    random_id = str(uuid.uuid4())
    url = f"{BASE_URL}/users/{random_id}/register/deny"
    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    err = resp.json()
    assert err.get("detail") == "User not found."


@pytest.mark.integration
def test_register_deny_self_forbidden(current_user_id):
    """PUT /users/{me}/register/deny should return 403 with detail 'Users cannot approve themselves.'."""
    url = f"{BASE_URL}/users/{current_user_id}/register/deny"
    resp = requests.put(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}"
    err = resp.json()
    assert err.get("detail") == "Users cannot approve themselves."


# =======================================
#   POST users
# =======================================


@pytest.fixture(scope="function")
def invited_user():
    """Invite a fresh user (no organization), yield the created record and then delete it in teardown."""
    email = f"invite_test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "first_name": "Invite",
        "last_name": "Test",
        "email": email,
    }

    # Setup: invite
    resp = requests.post(
        f"{BASE_URL}/users", json=payload, headers=HEADERS, timeout=TIMEOUT
    )
    assert resp.status_code == 200, f"Invite failed: {resp.status_code}"
    user = resp.json()

    yield user, payload

    # Teardown: delete the invited user
    del_resp = requests.delete(
        f"{BASE_URL}/users/{user['id']}", headers=HEADERS, timeout=TIMEOUT
    )
    assert del_resp.status_code in (200, 404), f"Cleanup failed: {del_resp.status_code}"


@pytest.mark.integration
def test_invite_user_success_no_org(invited_user):
    """
    POST /users.

    - returns 200
    - returns the new user's record
    - email is lowercased
    - invite_pending is True
    - no roles assigned
    """
    user, payload = invited_user
    assert user["email"] == payload["email"].lower()
    assert user["first_name"] == payload["first_name"]
    assert user["last_name"] == payload["last_name"]
    assert user.get("invite_pending") is True
    assert isinstance(user.get("roles"), list) and user["roles"] == []


@pytest.mark.integration
def test_invite_user_with_org_success(sample_org):
    """
    POST /users with 'organization' set should return 200 and assign a role.

    when the API key’s user is an org admin for that organization.
    """
    org_id = sample_org["id"]
    email = f"invite_test_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "first_name": "Org",
        "last_name": "Invite",
        "email": email,
        "organization": org_id,
        "organization_admin": True,
    }

    resp = requests.post(
        f"{BASE_URL}/users", json=payload, headers=HEADERS, timeout=TIMEOUT
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    user = resp.json()

    assert user["email"] == email.lower()
    assert user["invite_pending"] is True

    roles = user.get("roles", [])
    assert isinstance(roles, list) and len(roles) == 1
    role = roles[0]
    assert role["approved"] is True
    assert role["role"] in ("user", "admin")
    assert role["organization"]["id"] == org_id

    # Cleanup
    del_resp = requests.delete(
        f"{BASE_URL}/users/{user['id']}", headers=HEADERS, timeout=TIMEOUT
    )
    assert del_resp.status_code in (200, 404)
