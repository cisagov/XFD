"""Test API integrity."""
# Standard Python Libraries
import os
import re

# Third-Party Libraries
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
import pytest
from xfd_api.views import api_router
from xfd_django.asgi import app

client = TestClient(app)

# Allow list: public endpoints for specific HTTP methods
PUBLIC_ENDPOINTS = {
    ("POST", "/auth/okta-callback"),
    ("POST", "/auth/callback"),
    ("GET", "/notifications"),
    ("GET", "/healthcheck"),
}

# HTTP methods to test
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]

# Generate all route-method combinations that require authentication
routes_to_test_auth = [
    (method, route.path)
    for route in api_router.routes
    for method in HTTP_METHODS
    if (method, route.path) not in PUBLIC_ENDPOINTS
]


@pytest.mark.parametrize("method, route", routes_to_test_auth)
def test_endpoints_require_auth(method, route):
    """Ensure all secured endpoints return 401 Unauthorized or 405 Method Not Allowed when accessed without authentication."""
    response = client.request(method, route)
    assert response.status_code in [
        401,
        405,
    ], "Expected 401 (unauthorized) or 405 (not a valid method) for {} {}, but got {}".format(
        method, route, response.status_code
    )


# Define an exclusion list for endpoints that do not require a response model
# TODO: Create response models for any endpoints excluded here that need them
EXCLUDED_ENDPOINTS_RESPONSE_MODEL = {
    ("GET", "/healthcheck"),
    ("GET", "/matomo/{path:path}"),
    ("GET", "/pe/{path:path}"),
    ("PUT", "/pe/{path:path}"),
    ("POST", "/pe/{path:path}"),
    ("DELETE", "/pe/{path:path}"),
    ("OPTIONS", "/pe/{path:path}"),
    ("DELETE", "/api-keys/{api_key_id}"),
    ("POST", "/auth/callback"),
    ("POST", "/auth/okta-callback"),
    ("POST", "/domain/export"),
    ("POST", "/vulnerabilities/export"),
    ("DELETE", "/notifications/{notification_id}"),
    ("POST", "/v2/organizations/{organization_id}/users"),
    ("POST", "/search/organizations"),
    ("DELETE", "/saved-searches/{saved_search_id}"),
    ("POST", "/scheduler/invoke"),
    ("POST", "/scan-tasks/{scan_task_id}/kill"),
    ("GET", "/scan-tasks/{scan_task_id}/logs"),
    ("POST", "/search/export"),
    ("GET", "/healthcheck"),
    ("GET", "/users/me"),
}

# Collect all route-method pairs
routes_to_test_response_models = [
    (route.path, method, route.response_model)
    for route in app.router.routes
    if isinstance(route, APIRoute)
    for method in route.methods  # Ensures each HTTP method is checked separately
    if (method, route.path)
    not in EXCLUDED_ENDPOINTS_RESPONSE_MODEL  # Skip excluded endpoints
]


# Require every API endpoint to have a response model
@pytest.mark.parametrize("path, method, response_model", routes_to_test_response_models)
def test_all_endpoints_have_response_model(path, method, response_model):
    """Ensure every API endpoint has a response model for each HTTP method."""
    assert response_model is not None, "Missing response model for {} {}".format(
        method, path
    )


# List of API routes with their methods
api_routes_test = [
    (method, route.path)
    for route in app.router.routes
    if isinstance(route, APIRoute)
    for method in route.methods
]

# Exclusion List: API calls we do NOT require tests for**
EXCLUDED_ENDPOINTS_TESTS = {
    ("GET", "/healthcheck"),  # Test not needed
    ("GET", "/matomo/{path:path}"),  # TODO
    ("GET", "/pe/{path:path}"),  # Tested
    ("PUT", "/pe/{path:path}"),  # Tested
    ("POST", "/pe/{path:path}"),  # Tested
    ("DELETE", "/pe/{path:path}"),  # Tested
    ("OPTIONS", "/pe/{path:path}"),  # Tested
    ("POST", "/auth/callback"),  # Not used
    ("POST", "/domain/export"),  # TODO
    ("POST", "/vulnerabilities/export"),  # TODO
    ("POST", "/services"),  # Tested by /stats
    ("POST", "/ports"),  # Tested by /stats
    ("POST", "/num-vulns"),  # Tested by /stats
    ("POST", "/latest-vulns"),  # Tested by /stats
    ("POST", "/most-common-vulns"),  # Tested by /stats
    ("POST", "/severity-counts"),  # Tested by /stats
    ("POST", "/by-org"),  # Tested by /stats
}


def convert_route_to_regex(route):
    """Convert FastAPI route format."""
    return re.sub(r"\{.*?\}", r"[^/]+", route)  # Convert `{param}` → `[^/]+`


@pytest.mark.parametrize("method, route", api_routes_test)
def test_all_endpoints_have_tests(method, route):
    """Ensure every API endpoint has a corresponding test, unless excluded."""
    if (method, route) in EXCLUDED_ENDPOINTS_TESTS:
        pytest.skip("Skipping test coverage check for {} {}".format(method, route))

    route_regex = convert_route_to_regex(route)  # Convert `{param}` → `[^/]+`
    test_files = [
        f
        for f in os.listdir("xfd_api/tests")
        if f.startswith("test_") and f.endswith(".py")
    ]

    found = False
    for test_file in test_files:
        with open(os.path.join("xfd_api/tests", test_file)) as f:
            test_content = f.read()

            # Match API calls:
            pattern = r'client\.{}\(\s*["\']{}'.format(method.lower(), route_regex)

            if re.search(pattern, test_content):
                found = True
                break  # Stop once a match is found

    assert found, "Missing test for {} {}".format(method, route)
