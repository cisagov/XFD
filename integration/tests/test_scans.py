"""Regression Tests for Scans Endpoint."""

# Standard Python Libraries
import os

# Third-Party Libraries
import pytest
import requests

# ——— Configuration ———
BASE_URL = os.environ.get("BACKEND_DOMAIN")
X_API_KEY = os.environ.get("X_API_KEY")
HEADERS = {"X-API-KEY": X_API_KEY}
BAD_HEADERS = {"X-API-KEY": "invalid-key"}
BAD_ID = "00000000-0000-0000-0000-000000000000"
INVALID = "notauuid"
BAD_KEY = "invalid_api_key"
TIMEOUT = 10


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
    """Pick one  organization from the list for downstream tests."""
    return all_organizations[0]


@pytest.fixture(scope="session")
def org_id(sample_org):
    """Retrieve organization id from sample org."""
    return sample_org["id"]


@pytest.fixture(scope="session")
def region_id(sample_org):
    """Retrieve region id from sample org."""
    return sample_org.get("region_id")


@pytest.fixture(scope="session")
def state(sample_org):
    """Retrieve state from sample org."""
    return sample_org.get("state")


@pytest.fixture(scope="session")
def name(sample_org):
    """Retrieve name from sample org."""
    return sample_org["name"]


@pytest.fixture
def test_scan(org_id):
    """Create a temporary scan via POST /scans using the required payload.

    Yields the new scan record, then deletes it after the test.
    """
    payload = {
        "name": "censys",
        "arguments": {},
        "organizations": [org_id],
        "tags": [],
        "frequency": 86400,
        "frequencyUnit": "day",
        "is_granular": True,
        "is_user_modifiable": True,
        "is_single_scan": False,
        "concurrent_tasks": 1,
    }

    # Create the scan
    resp = requests.post(
        f"{BASE_URL}/scans",
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Scan creation failed: {resp.status_code}"
    scan = resp.json()

    yield scan

    # Teardown: delete the scan
    try:
        del_resp = requests.delete(
            f"{BASE_URL}/scans/{scan['id']}",
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        assert del_resp.status_code in (
            200,
            404,
        ), f"Scan deletion failed: {del_resp.status_code}"
    except Exception as e:
        print(f"Warning: failed to delete scan {scan.get('id')}: {e}")


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


@pytest.mark.integration
@pytest.mark.parametrize("headers", [None, BAD_HEADERS], ids=["no-auth", "bad-auth"])
@pytest.mark.parametrize(
    "method, endpoint_template",
    [
        ("GET", "/scans"),
        ("GET", "/granularScans"),
        ("GET", "/scans/{scan_id}"),
        ("POST", "/scans"),
        ("POST", "/scans/{scan_id}/run"),
        ("POST", "/scheduler/invoke"),
        ("DELETE", "/scans/{scan_id}"),
        ("PUT", "/scans/{scan_id}"),
    ],
)
def test_auth_failure_single_request(headers, method, endpoint_template, test_scan):
    """Each (method, URL, auth header) pair is its own test."""
    url = f"{BASE_URL}" + endpoint_template.format(scan_id=test_scan["id"])
    resp = requests.request(method, url, headers=headers, timeout=TIMEOUT)
    context = f"[{method} {url}] "
    assert_auth_failure(resp, context)


@pytest.mark.integration
@pytest.mark.parametrize(
    "method, endpoint_template",
    [
        ("POST", "/granularScans"),
        ("GET", "/scans/{scan_id}/run"),
        ("GET", "/scheduler/invoke"),
    ],
)
def test_methods_not_allowed(method, endpoint_template, test_scan):
    """Ensure that unsupported methods return 405 with real IDs."""
    url = f"{BASE_URL}" + endpoint_template.format(scan_id=test_scan["id"])

    resp = requests.request(method, url, headers=HEADERS, timeout=TIMEOUT)
    assert (
        resp.status_code == 405
    ), f"[{method} {url}] Expected 405, got {resp.status_code}"


# ========================================
#   GET Scans
# ========================================


@pytest.mark.integration
def test_list_scans_success(test_scan):
    """GET /Scans should return 200 and a list under "scans"."""
    resp = requests.get(f"{BASE_URL}/scans", headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200
    scans = resp.json().get("scans", resp.json())
    assert isinstance(scans, list) and scans


@pytest.mark.integration
def test_list_scans_includes_created_scan(test_scan):
    """
    GET /Scans should return 200 and a list under "scans".

    Including the scan created by test_scan.
    """
    resp = requests.get(f"{BASE_URL}/scans", headers=HEADERS, timeout=TIMEOUT)
    scans = resp.json().get("scans", resp.json())
    ids = [s["id"] for s in scans]
    assert test_scan["id"] in ids
    scan_obj = next(s for s in scans if s["id"] == test_scan["id"])
    assert scan_obj["name"] == "censys"
    assert scan_obj["is_granular"] and scan_obj["is_user_modifiable"]


# ========================================
#   GET grandularScans
# ========================================


@pytest.mark.integration
def test_list_granular_scans_success(test_scan):
    """
    GET /granularScans should return 200 and a list under "scans".

    Including the scan created by test_scan.
    """
    url = f"{BASE_URL}/granularScans"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"

    body = resp.json()
    assert "scans" in body, "Response JSON must have a 'scans' key"
    scans = body["scans"]

    assert isinstance(scans, list), "'scans' must be a list"
    assert scans, "Expected at least one granular scan"

    for scan in scans:
        assert "id" in scan and scan["id"], "Each scan needs a non‑empty 'id'"
        assert "name" in scan and isinstance(
            scan["name"], str
        ), "Each scan needs a 'name'"
        assert "is_user_modifiable" in scan and isinstance(
            scan["is_user_modifiable"], bool
        ), "Each scan needs a boolean 'is_user_modifiable'"
    created_id = test_scan["id"]
    ids = [s["id"] for s in scans]
    assert created_id in ids, "Created granular scan not found in response"

    created = next(s for s in scans if s["id"] == created_id)
    assert created["name"] == "censys"
    assert created["is_user_modifiable"] is True


# ========================================
#   GET Scans scan_id
# ========================================


@pytest.mark.integration
def test_get_scan_success(test_scan):
    """GET /scans/{scan_id} should return 200 and the scan created by test_scan."""
    scan_id = test_scan["id"]
    url = f"{BASE_URL}/scans/{scan_id}"
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"

    body = resp.json()
    assert body["scan"]["id"] == scan_id
    assert body["scan"]["name"] == test_scan["name"]
    assert body["scan"]["is_granular"] is True
    assert body["scan"]["is_user_modifiable"] is True


@pytest.mark.integration
def test_get_scan_not_found():
    """GET /scans/{scan_id} with a non‑existent ID should return 404."""
    url = f"{BASE_URL}/scans/{BAD_ID}"

    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"


@pytest.mark.integration
def test_get_scan_invalid():
    """GET /scans/{scan_id} with invalid value should return 500."""
    url = f"{BASE_URL}/scans/{INVALID}"

    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    assert resp.status_code == 500, f"Expected 500 Not Found, got {resp.status_code}"


# ========================================
#   POST Scans
# ========================================


def make_payload(org_id, name="censys"):
    """Return a valid scan payload, using an existing scan name."""
    return {
        "name": name,
        "arguments": {},
        "organizations": [org_id],
        "tags": [],
        "frequency": 86400,
        "frequencyUnit": "day",
        "is_granular": True,
        "is_user_modifiable": True,
        "is_single_scan": False,
        "concurrent_tasks": 1,
    }


@pytest.mark.integration
def test_create_and_delete_scan(org_id):
    """Create a scan, verify it, delete it, and confirm deletion."""
    payload = make_payload(org_id)
    scan_id = None

    try:
        resp = requests.post(
            f"{BASE_URL}/scans",
            json=payload,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, f"Create failed: {resp.status_code} {resp.text}"
        scan = resp.json()
        scan_id = scan["id"]

        assert scan["name"] == payload["name"]
        returned_orgs = [o["id"] for o in scan["organizations"]]
        assert org_id in returned_orgs

    finally:
        if scan_id:
            del_resp = requests.delete(
                f"{BASE_URL}/scans/{scan_id}",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            assert del_resp.status_code in (
                200,
                204,
            ), f"Delete failed: {del_resp.status_code}"

            get_resp = requests.get(
                f"{BASE_URL}/scans/{scan_id}",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            assert get_resp.status_code == 404, "Deleted scan still accessible"


@pytest.mark.integration
def test_create_scan_missing_required_fields():
    """422 if required fields (name, organizations) are missing."""
    bad_payload = {
        "arguments": {},
        "tags": [],
        "frequency": 86400,
        "frequencyUnit": "day",
        "is_granular": True,
        "is_user_modifiable": True,
        "is_single_scan": False,
        "concurrent_tasks": 1,
    }
    resp = requests.post(
        f"{BASE_URL}/scans",
        json=bad_payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.integration
def test_create_scan_invalid_field_types(org_id):
    """422 if a field has the wrong type (e.g. frequency as string)."""
    payload = make_payload(org_id)
    payload["frequency"] = "not-a-number"
    resp = requests.post(
        f"{BASE_URL}/scans",
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


# ========================================
#   PUT Scans
# ========================================


@pytest.mark.integration
def test_update_success(test_scan):
    """PUT a valid scan_id should update and return 200."""
    payload = {
        "name": "updated scan name",
        "arguments": {},
        "tags": [],
        "frequency": 43200,
        "frequencyUnit": "hour",
        "is_granular": True,
        "is_user_modifiable": True,
        "is_single_scan": False,
    }

    resp = requests.put(
        f"{BASE_URL}/scans/{test_scan['id']}",
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert (
        resp.status_code == 200
    ), f"Unexpected status: {resp.status_code} - {resp.text}"

    scan = resp.json()

    assert scan["name"] == payload["name"]
    assert scan["arguments"] == payload["arguments"]
    assert scan["frequency"] == payload["frequency"]
    assert scan["is_granular"] == payload["is_granular"]
    assert scan["is_user_modifiable"] == payload["is_user_modifiable"]
    assert scan["is_single_scan"] == payload["is_single_scan"]

    assert scan["tags"] == []

    original_orgs = [org["id"] for org in test_scan["organizations"]]
    updated_orgs = [org["id"] for org in scan["organizations"]]
    assert original_orgs == updated_orgs


# ─── Helpers ────────────────────────────────────────────────────────────────────
def make_update_payload(scan_id, original_scan, new_name="patched scan"):
    """
    Build a valid payload for PUT /scans/{scan_id}.

    re‑using required fields from the original scan (organizations & concurrent_tasks).
    """
    org_ids = [o["id"] for o in original_scan["organizations"]]
    return {
        "name": new_name,
        "arguments": {"foo": "bar"},
        "organizations": org_ids,
        "tags": ["updated"],
        "frequency": 3600,
        "frequencyUnit": "hour",
        "is_granular": original_scan["is_granular"],
        "is_user_modifiable": original_scan["is_user_modifiable"],
        "is_single_scan": original_scan["is_single_scan"],
        "concurrent_tasks": original_scan["concurrent_tasks"],
    }


@pytest.mark.integration
def test_update_scan_not_found(org_id):
    """PUT a non‑existent scan_id should return 404."""
    payload = {
        "name": "won't matter",
        "arguments": {},
        "organizations": [org_id],
        "tags": [],
        "frequency": 100,
        "frequencyUnit": "day",
        "is_granular": False,
        "is_user_modifiable": False,
        "is_single_scan": False,
        "concurrent_tasks": 1,
    }

    resp = requests.put(
        f"{BASE_URL}/scans/{BAD_ID}",
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.integration
def test_update_scan_invalid(org_id):
    """PUT a invalid value should return 500."""
    payload = {
        "name": "won't matter",
        "arguments": {},
        "organizations": [org_id],
        "tags": [],
        "frequency": 100,
        "frequencyUnit": "day",
        "is_granular": False,
        "is_user_modifiable": False,
        "is_single_scan": False,
        "concurrent_tasks": 1,
    }

    resp = requests.put(
        f"{BASE_URL}/scans/{INVALID}",
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"


@pytest.mark.integration
def test_update_scan_missing_required_fields(test_scan):
    """PUT with missing required fields should return 422 Unprocessable Entity."""
    scan_id = test_scan["id"]
    bad_payload = {
        "arguments": {},
        "tags": [],
        "frequency": 123,
        "frequencyUnit": "day",
        "is_granular": True,
        "is_user_modifiable": True,
        "is_single_scan": False,
        "concurrent_tasks": 1,
    }

    resp = requests.put(
        f"{BASE_URL}/scans/{scan_id}",
        json=bad_payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


@pytest.mark.integration
def test_update_scan_invalid_field_types(test_scan):
    """PUT with a wrong type (e.g. 'frequency' as string) should return 422."""
    scan_id = test_scan["id"]
    payload = make_update_payload(scan_id, test_scan)
    payload["frequency"] = "not-an-integer"

    resp = requests.put(
        f"{BASE_URL}/scans/{scan_id}",
        json=payload,
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"


# ========================================
#   Delete Scans
# ========================================


@pytest.mark.integration
def test_delete_scan_success(test_scan):
    """
    DELETE an existing scan should return 200 (or 204) and remove it.

    The test_scan fixture created the scan, so we just delete it here.
    """
    scan_id = test_scan["id"]

    del_resp = requests.delete(
        f"{BASE_URL}/scans/{scan_id}",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert del_resp.status_code in (
        200,
        204,
    ), f"Unexpected status: {del_resp.status_code}"
    if del_resp.status_code == 200:
        body = del_resp.json()
        assert "message" in body and isinstance(body["message"], str)

    get_resp = requests.get(
        f"{BASE_URL}/scans/{scan_id}",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert get_resp.status_code == 404, "Deleted scan still accessible"


@pytest.mark.integration
def test_delete_scan_not_found():
    """DELETE a non-existent scan should return 404 Not Found."""
    resp = requests.delete(
        f"{BASE_URL}/scans/{BAD_ID}",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"


@pytest.mark.integration
def test_delete_scan_invalid():
    """DELETE a non-existent scan should return 500 Not Found."""
    resp = requests.delete(
        f"{BASE_URL}/scans/{INVALID}",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 500, f"Expected 500, got {resp.status_code}"


# ========================================
#   POST run scan
# ========================================


@pytest.mark.integration
def test_run_scan_success(test_scan):
    """POST /scans/{scan_id}/run should return 200 and a JSON message when called on an existing scan."""
    scan_id = test_scan["id"]
    resp = requests.post(
        f"{BASE_URL}/scans/{scan_id}/run",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    body = resp.json()
    assert "message" in body and isinstance(body["message"], str)


@pytest.mark.integration
def test_run_scan_not_found():
    """POST /scans/{scan_id}/run for a non-existent ID should return 404."""
    resp = requests.post(
        f"{BASE_URL}/scans/{BAD_ID}/run",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"


@pytest.mark.integration
def test_run_scan_invalid():
    """POST /scans/{scan_id}/run for a non-existent ID should return 500."""
    resp = requests.post(
        f"{BASE_URL}/scans/{INVALID}/run",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 500, f"Expected 500 Not Found, got {resp.status_code}"


# ========================================
#   POST Scheduler
# ========================================


@pytest.mark.integration
def test_invoke_scheduler_success():
    """POST /scheduler/invoke should return 200 OK and a JSON with a 'message' field."""
    resp = requests.post(
        f"{BASE_URL}/scheduler/invoke",
        headers=HEADERS,
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    body = resp.json()
    assert isinstance(body, dict), "Response should be a JSON object"
    assert "message" in body and isinstance(
        body["message"], str
    ), "Response JSON must contain a string 'message'"
