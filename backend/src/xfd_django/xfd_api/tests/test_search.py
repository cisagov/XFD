# test_search.py
# Third-Party Libraries
from fastapi.testclient import TestClient

# from xfd_api.views import api_router
from xfd_django.asgi import app

client = TestClient(app)

# Example search body to use for testing
search_body = {
    "current": 1,
    "results_per_page": 10,
    "search_term": "example search term",
    "sort_direction": "asc",
    "sort_field": "createdAt",
    "filters": [{"field": "organization.id", "values": ["1", "2", "3"], "type": "any"}],
    "organization_ids": ["f834b2f8-3c10-4d3a-8ec7-9fc57b88c9e5"],
    "organization_id": "f834b2f8-3c10-4d3a-8ec7-9fc57b88c9e5",
    "tag_id": "a93a5d1b-1234-4567-890a-bc1234567890",
}


# Test for /search endpoint
def test_search_endpoint():
    response = client.post("/search", json=search_body)
    assert response.status_code == 200  # Expecting HTTP 200 OK
    data = response.json()
    assert "current" in data  # Check if the expected field is in the response
    assert data["current"] == 1  # Ensure the current value matches the request


# Test for /search/export endpoint
def test_search_export_endpoint():
    response = client.post("/search/export", json=search_body)
    assert response.status_code == 200  # Expecting HTTP 200 OK
    data = response.json()
    assert "url" in data  # Check if the response contains the CSV URL


# Test for invalid request to /search endpoint (missing required fields)
def test_search_invalid_request():
    invalid_body = {"current": 1}  # Missing many required fields
    response = client.post("/search", json=invalid_body)
    assert response.status_code == 422  # Expecting validation error


# Test for invalid request to /search/export endpoint (missing required fields)
def test_search_export_invalid_request():
    invalid_body = {"current": 1}  # Missing many required fields
    response = client.post("/search/export", json=invalid_body)
    assert response.status_code == 422  # Expecting validation error
