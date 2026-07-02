"""Test CVE/CPE."""
# Standard Python Libraries
from datetime import datetime
import secrets
from unittest.mock import patch
import uuid

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import Cpe, Cve, Organization, Role, User, UserType

client = TestClient(app)


@pytest.fixture
def simple_cve_index():
    """Mock simple in-memory CVE index."""
    return [
        {"_source": {"name": "CVE-2024-0001", "organization_ids": []}},
        {"_source": {"name": "CVE-2025-0002", "organization_ids": []}},
        {"_source": {"name": "CVE-2026-0003", "organization_ids": []}},
        {"_source": {"name": "CVE-2027-0001", "organization_ids": []}},
    ]


@pytest.fixture
def mock_es_search_simple(simple_cve_index):
    """Mock that queries simple index based on query_body."""

    def search_impl(query_body):
        results = []

        # Extract search term from wildcard query
        search_term = None
        for clause in query_body.get("query", {}).get("bool", {}).get("must", []):
            if "wildcard" in clause:
                wildcard = clause["wildcard"]["name.keyword"]
                search_term = wildcard.strip("*")
                break

        # Extract org filter
        org_filter = None
        for f in query_body.get("query", {}).get("bool", {}).get("filter", []):
            if "terms" in f:
                org_filter = f["terms"]["organization_ids"]
                break

        # Filter index
        for cve in simple_cve_index:
            if search_term and search_term not in cve["_source"]["name"]:
                continue
            if org_filter and not any(
                str(org) in cve["_source"]["organization_ids"] for org in org_filter
            ):
                continue
            results.append(cve)

        return {"hits": {"hits": results}}

    return search_impl


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_cpe_by_id_success():
    """Test successfully retrieving a CPE by ID."""
    # Create a user to authenticate the request
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Create a sample CPE record
    cpe = Cpe.objects.create(
        id=uuid.uuid4(),
        name="cpe:/o:test_os:1.0",
        version="1.0.0",
        vendor="TestVendor",
        last_seen_at=datetime.now(),
    )

    # Make the request
    response = client.get(
        "/cpes/{}".format(cpe.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(cpe.id)
    assert data["name"] == "cpe:/o:test_os:1.0"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_cpe_by_id_not_found():
    """Test retrieving a non-existent CPE should return a 500 error."""
    # Create a user to authenticate the request
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    fake_cpe_id = uuid.uuid4()

    # Make the request with a non-existent CPE ID
    response = client.get(
        "/cpes/{}".format(fake_cpe_id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 500
    assert "detail" in response.json()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_cve_by_id_success():
    """Test successfully retrieving a CVE by ID."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    cve = Cve.objects.create(
        id=uuid.uuid4(),
        name="CVE-2024-1234",
        description="Test CVE description",
        published_at=datetime.now(),
        modified_at=datetime.now(),
        status="Active",
        cvss_v3_base_score="9.8",
        cvss_v3_base_severity="Critical",
        weaknesses=["None"],
        reference_urls=["https://cve.mitre.org"],
    )

    response = client.get(
        "/cves/{}".format(cve.id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(cve.id)
    assert data["name"] == "CVE-2024-1234"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_cve_by_id_not_found():
    """Test retrieving a non-existent CVE should return a 500 error."""
    # Create a user to authenticate the request
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    fake_cve_id = uuid.uuid4()

    # Make the request with a non-existent CVE ID
    response = client.get(
        "/cves/{}".format(fake_cve_id),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 500
    assert "detail" in response.json()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_cve_by_name_success():
    """Test successfully retrieving a CVE by name."""
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    cve = Cve.objects.create(
        id=uuid.uuid4(),
        name="CVE-2024-5678",
        description="Another test CVE",
        published_at=datetime.now(),
        modified_at=datetime.now(),
        status="Resolved",
        cvss_v2_base_score="5.0",
        cvss_v2_base_severity="Medium",
    )

    response = client.get(
        "/cves/name/{}".format(cve.name),
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CVE-2024-5678"
    assert data["description"] == "Another test CVE"
    assert data["status"] == "Resolved"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_cve_by_name_not_found():
    """Test retrieving a non-existent CVE by name should return a 500 error."""
    # Create a user to authenticate the request
    user = User.objects.create(
        first_name="Test",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Make the request with a non-existent CVE name
    response = client.get(
        "/cves/name/CVE-9999-9999",
        headers={"Authorization": "Bearer {}".format(create_jwt_token(user))},
    )

    assert response.status_code == 500
    assert "detail" in response.json()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_cves")
def test_search_cves_as_global_admin(
    mock_search, simple_cve_index, mock_es_search_simple
):
    """Test that a GlobalViewAdmin can search CVEs."""
    admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    org = Organization.objects.create(
        name="TestOrg-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id=1,
    )

    Role.objects.create(
        user=admin,
        organization=org,
        role="admin",
    )
    # Mock Elasticsearch to return CVEs from multiple organizations, including the one the admin belongs to.
    simple_cve_index[0]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[1]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[2]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[3]["_source"]["organization_ids"] = [str(uuid.uuid4())]

    mock_search.side_effect = mock_es_search_simple

    payload = {"search_term": "202"}

    response = client.post(
        "/search/cves",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "body" in data
    # Verify that the admin can see all CVEs, regardless of organization
    assert len(data["body"]["hits"]["hits"]) == 4


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_cves")
def test_full_text_search_cves_as_global_admin(
    mock_search, simple_cve_index, mock_es_search_simple
):
    """Test that a Global Admin only returns exact match with full text search CVEs from multiple organizations."""
    admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    org = Organization.objects.create(
        name="TestOrg-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id=1,
    )

    Role.objects.create(
        user=admin,
        organization=org,
        role="admin",
    )
    # Mock Elasticsearch to return CVEs from multiple organizations, including the one the admin belongs to.
    simple_cve_index[0]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[1]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[2]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[3]["_source"]["organization_ids"] = [str(uuid.uuid4())]

    mock_search.side_effect = mock_es_search_simple

    payload = {"search_term": "CVE-2026-0003"}

    response = client.post(
        "/search/cves",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "body" in data
    # Verify that the admin can see the specific CVE
    assert len(data["body"]["hits"]["hits"]) == 1
    assert data["body"]["hits"]["hits"][0]["_source"]["name"] == "CVE-2026-0003"


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_cves")
def test_empty_text_search_cves_as_global_admin(
    mock_search, simple_cve_index, mock_es_search_simple
):
    """Test that a Global Admin returns all CVEs from multiple organizations when search term is empty."""
    admin = User.objects.create(
        first_name="Admin",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    org = Organization.objects.create(
        name="TestOrg-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id=1,
    )

    Role.objects.create(
        user=admin,
        organization=org,
        role="admin",
    )
    # Mock Elasticsearch to return CVEs from multiple organizations, including the one the admin belongs to.
    simple_cve_index[0]["_source"]["name"] = "CVE-1024-0001"
    simple_cve_index[0]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[1]["_source"]["name"] = "CVE-2234-0002"
    simple_cve_index[1]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[2]["_source"]["name"] = "CVE-2026-0003"
    simple_cve_index[2]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[3]["_source"]["name"] = "CVE-4567-0004"
    simple_cve_index[3]["_source"]["organization_ids"] = [str(uuid.uuid4())]

    mock_search.side_effect = mock_es_search_simple

    payload = {"search_term": ""}

    response = client.post(
        "/search/cves",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(admin))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "body" in data
    # Verify that the admin can see all CVEs, regardless of organization
    assert len(data["body"]["hits"]["hits"]) == 4


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_cves")
def test_search_cves_as_standard_user(
    mock_search, simple_cve_index, mock_es_search_simple
):
    """Test that a Standard User only returns CVEs from their organization."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    org = Organization.objects.create(
        name="AuthorizedOrg-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id=1,
    )

    # Assign organization to authorized user
    Role.objects.create(
        user=standard_user,
        organization=org,
        role="user",
    )

    simple_cve_index[0]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[1]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[2]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[3]["_source"]["organization_ids"] = [str(uuid.uuid4())]

    mock_search.side_effect = mock_es_search_simple

    payload = {"search_term": "202"}

    response = client.post(
        "/search/cves",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "body" in data
    assert len(data["body"]["hits"]["hits"]) == 2
    assert data["body"]["hits"]["hits"][0]["_source"]["name"] == "CVE-2024-0001"
    assert data["body"]["hits"]["hits"][1]["_source"]["name"] == "CVE-2026-0003"
    # Ensure all returned CVEs belong to the user's organization
    assert all(
        str(org.id) in hit["_source"]["organization_ids"]
        for hit in data["body"]["hits"]["hits"]
    )
    # Ensure the organization_ids in the first hit matches the user's organization
    # assert data["body"]["hits"]["hits"][0]["_source"]["organization_ids"] == [str(org.id)]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_cves")
def test_full_text_search_cves_as_standard_user(
    mock_search, simple_cve_index, mock_es_search_simple
):
    """Test that a Standard User only returns exact match with full text search CVEs from their organization."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    org = Organization.objects.create(
        name="AuthorizedOrg-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id=1,
    )

    # Assign organization to authorized user
    Role.objects.create(
        user=standard_user,
        organization=org,
        role="user",
    )

    simple_cve_index[0]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[1]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[2]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[3]["_source"]["organization_ids"] = [str(uuid.uuid4())]

    mock_search.side_effect = mock_es_search_simple

    payload = {"search_term": "CVE-2024-0001"}

    response = client.post(
        "/search/cves",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "body" in data
    assert len(data["body"]["hits"]["hits"]) == 1
    assert data["body"]["hits"]["hits"][0]["_source"]["name"] == "CVE-2024-0001"
    # Ensure the returned CVE belongs to the user's organization
    assert str(org.id) in data["body"]["hits"]["hits"][0]["_source"]["organization_ids"]


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_cves")
def test_empty_text_search_cves_as_standard_user(
    mock_search, simple_cve_index, mock_es_search_simple
):
    """Test that a Standard User only returns all CVEs from their organization when search term is empty."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    org = Organization.objects.create(
        name="AuthorizedOrg-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id=1,
    )

    # Assign organization to authorized user
    Role.objects.create(
        user=standard_user,
        organization=org,
        role="user",
    )

    simple_cve_index[0]["_source"]["name"] = "CVE-1024-0001"
    simple_cve_index[0]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[1]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[2]["_source"]["organization_ids"] = [str(org.id)]
    simple_cve_index[3]["_source"]["organization_ids"] = [str(uuid.uuid4())]

    mock_search.side_effect = mock_es_search_simple

    payload = {"search_term": ""}

    response = client.post(
        "/search/cves",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "body" in data
    # The user should see all CVEs from their organization
    assert len(data["body"]["hits"]["hits"]) == 2
    assert data["body"]["hits"]["hits"][0]["_source"]["name"] == "CVE-1024-0001"
    assert data["body"]["hits"]["hits"][1]["_source"]["name"] == "CVE-2026-0003"
    # Ensure all returned CVEs belong to the user's organization
    assert all(
        str(org.id) in hit["_source"]["organization_ids"]
        for hit in data["body"]["hits"]["hits"]
    )


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
@patch("xfd_api.tasks.es_client.ESClient.search_cves")
def test_search_cves_as_standard_user_incorrect_org(
    mock_search, simple_cve_index, mock_es_search_simple
):
    """Test that a Standard User cannot access CVEs from an unauthorized organization."""
    standard_user = User.objects.create(
        first_name="Standard",
        last_name="User",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    org = Organization.objects.create(
        name="UnauthorizedOrg-{}".format(secrets.token_hex(4)),
        root_domains=["test-{}".format(secrets.token_hex(4))],
        ip_blocks=[],
        is_passive=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        region_id=1,
    )

    # Assign organization to authorized user
    Role.objects.create(
        user=standard_user,
        organization=org,
        role="user",
    )

    # Mock Elasticsearch to return CVEs from a different organization
    simple_cve_index[0]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[1]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[2]["_source"]["organization_ids"] = [str(uuid.uuid4())]
    simple_cve_index[3]["_source"]["organization_ids"] = [str(uuid.uuid4())]

    mock_search.side_effect = mock_es_search_simple

    payload = {"search_term": "202"}

    response = client.post(
        "/search/cves",
        json=payload,
        headers={"Authorization": "Bearer {}".format(create_jwt_token(standard_user))},
    )

    assert response.status_code == 200
    data = response.json()
    assert "body" in data
    # The user should not see any CVEs from unauthorized organizations
    assert len(data["body"]["hits"]["hits"]) == 0


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_search_cves_no_auth():
    """Test that a request without authentication returns 403."""
    payload = {"search_term": "No Auth Test"}

    response = client.post("/search/cves", json=payload)

    assert response.status_code == 401
    assert response.json() == {"detail": "No valid authentication credentials provided"}
