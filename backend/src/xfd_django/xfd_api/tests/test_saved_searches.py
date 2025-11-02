"""Test saved search."""
# Standard Python Libraries
from datetime import datetime
import secrets

# Third-Party Libraries
from fastapi.testclient import TestClient
import pytest
from xfd_api.auth import create_jwt_token
from xfd_django.asgi import app
from xfd_mini_dl.models import SavedSearch, User, UserType

client = TestClient(app)


@pytest.fixture
def create_global_admin():
    """Create user fixture."""
    global_admin_user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_ADMIN,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    yield global_admin_user
    global_admin_user.delete()


@pytest.fixture
def create_global_view():
    """Create user fixture."""
    global_view_user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.GLOBAL_VIEW,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    yield global_view_user
    global_view_user.delete()


@pytest.fixture
def create_standard_user():
    """Create user fixture."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    yield user
    user.delete()


@pytest.fixture
def create_secondary_standard_user():
    """Create user fixture."""
    user = User.objects.create(
        first_name="",
        last_name="",
        email="{}@example.com".format(secrets.token_hex(4)),
        user_type=UserType.STANDARD,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    yield user
    user.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_create_saved_search_by_user(create_standard_user):
    """
    Ensure that a standard user can successfully create a saved search.

    This test verifies that a user with standard permissions can create a saved search by sending a POST request with the appropriate JSON payload.
    The test checks the response status code and the data to confirm that the saved search is created successfully.
    Assertions:
        The response status code should be 200.
        The response data should include the correct name and createdById fields.
    """
    user = create_standard_user
    name = "test-{}".format(secrets.token_hex(4))
    response = client.post(
        "/saved-searches",
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
        json={
            "name": name,
            "count": 3,
            "sort_direction": "",
            "sort_field": "",
            "search_term": "",
            "search_path": "",
            "filters": [],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == name
    assert data["created_by_id"] == str(user.id)
    search = SavedSearch.objects.get(id=data["id"])
    search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_saved_search_by_global_admin_fails(
    create_global_admin, create_standard_user
):
    """
    Ensure that a global admin user cannot update a saved search created by another user.

    This test attempts to update a saved search using the global admin's credentials and asserts that the operation fails with a 404 status code.
    Assertions:
        The response status code should be 404.
    """
    global_admin_user = create_global_admin
    standard_user = create_standard_user
    body = {
        "name": "test-{}".format(secrets.token_hex(4)),
        "count": 3,
        "sort_direction": "",
        "sort_field": "",
        "search_term": "",
        "search_path": "",
        "filters": [],
        "updated_at": datetime.now(),  # Include updatedAt field
    }
    search = SavedSearch.objects.create(**body, created_by=standard_user)
    body["name"] = "test-{}".format(secrets.token_hex(4))
    body["search_term"] = "123"
    body["updated_at"] = datetime.now().isoformat()  # Update the timestamp

    response = client.post(
        "/update_saved-searches/{}".format(search.id),
        json=body,
        headers={"Authorization": "Bearer " + create_jwt_token(global_admin_user)},
    )
    assert response.status_code == 404

    # Cleanup
    search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_saved_search_by_global_view_fails(
    create_standard_user, create_global_view
):
    """
    Ensure that a global view user cannot update a saved search.

    This test verifies that a user with global view permissions is not allowed to update a saved search created by a standard user.
    It attempts to update the saved search using the global view user's credentials and asserts that the operation fails with a 404 status code.
    Args:
        create_standard_user (function): Fixture to create a standard user.
        create_global_view (function): Fixture to create a global view user.
    Assertions:
        The response status code should be 404, indicating that the update operation is not permitted for the global view user.
    """
    global_view_user = create_global_view
    user = create_standard_user
    body = {
        "name": "test-{}".format(secrets.token_hex(4)),
        "count": 3,
        "sort_direction": "",
        "sort_field": "",
        "search_term": "",
        "search_path": "",
        "filters": [],
        "updated_at": datetime.now(),  # Include updatedAt field
    }
    saved_search = SavedSearch.objects.create(**body, created_by=user)

    # Attempt to update the saved search with the global view user
    body["name"] = "test-{}".format(secrets.token_hex(4))
    body["search_term"] = "123"
    body["updated_at"] = datetime.now().isoformat()  # Update the timestamp
    response = client.post(
        "/update_saved-searches/{}".format(saved_search.id),
        json=body,
        headers={"Authorization": "Bearer " + create_jwt_token(global_view_user)},
    )

    # Assert that the response indicates failure (403 or 404)
    assert response.status_code == 404

    # Cleanup
    saved_search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_saved_search_by_standard_user_with_access(create_standard_user):
    """
    Ensure that a standard user with access can successfully update a saved search.

    This test verifies that a standard user who created the saved search can update it by sending a PUT request with updated data.
    Assertions:
        The response status code should be 200.
        The response data should include the updated name and searchTerm fields.
    """
    user = create_standard_user
    body = {
        "name": "test-{}".format(secrets.token_hex(4)),
        "count": 3,
        "sort_direction": "",
        "sort_field": "",
        "search_term": "",
        "search_path": "",
        "filters": [],
        "updated_at": datetime.now(),  # Include updatedAt field
    }
    search = SavedSearch.objects.create(**body, created_by=user)
    body["name"] = "test-{}".format(secrets.token_hex(4))
    body["search_term"] = "123"
    body["updated_at"] = datetime.now().isoformat()  # Update the timestamp

    response = client.post(
        "/update_saved-searches/{}".format(search.id),
        json=body,
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == body["name"]
    assert data["search_term"] == body["search_term"]

    # Cleanup
    search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_update_saved_search_by_standard_user_without_access_fails(
    create_standard_user, create_secondary_standard_user
):
    """
    Ensure that a standard user without access cannot update a saved search.

    This test verifies that a standard user cannot update a saved search created by another user.
    Assertions:
        The response status code should be 404.
    """
    user_with_access = create_standard_user
    user_without_access = create_secondary_standard_user
    body = {
        "name": "test-{}".format(secrets.token_hex(4)),
        "count": 3,
        "sort_direction": "",
        "sort_field": "",
        "search_term": "",
        "search_path": "",
        "filters": [],
        "updated_at": str(datetime.now()),  # Include updatedAt field
    }
    search = SavedSearch.objects.create(**body, created_by=user_with_access)
    response = client.post(
        "/update_saved-searches/{}".format(search.id),
        json=body,
        headers={"Authorization": "Bearer " + create_jwt_token(user_without_access)},
    )
    assert response.status_code == 404

    # Cleanup
    search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_saved_search_by_global_admin_fails(
    create_global_admin, create_standard_user
):
    """
    Ensure that a global admin user cannot delete a saved search created by another user.

    This test attempts to delete a saved search using the global admin's credentials and asserts that the operation fails with a 404 status code.
    Assertions:
        The response status code should be 404.
    """
    global_admin_user = create_global_admin
    standard_user = create_standard_user

    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=standard_user,
    )
    response = client.delete(
        "/saved-searches/{}".format(search.id),
        headers={"Authorization": "Bearer " + create_jwt_token(global_admin_user)},
    )
    assert response.status_code == 404

    # Cleanup
    if search:
        search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_saved_search_by_global_view_fails(
    create_standard_user, create_global_view
):
    """
    Ensure that a global view user cannot delete a saved search.

    This test verifies that a user with global view permissions is not allowed to delete a saved search created by a standard user.
    It attempts to delete the saved search using the global view user's credentials and asserts that the operation fails with a 404 status code.
    Args:
        create_standard_user (function): Fixture to create a standard user.
        create_global_view (function): Fixture to create a global view user.
    Assertions:
        The response status code should be 404, indicating that the delete operation is not permitted for the global view user.
    """
    global_view_user = create_global_view
    user = create_standard_user

    saved_search = SavedSearch.objects.create(
        name="test-search-{}".format(secrets.token_hex(4)),
        count=5,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=user,
    )

    # Attempt to delete the saved search with the global view user
    response = client.delete(
        "/saved-searches/{}".format(saved_search.id),
        headers={"Authorization": "Bearer " + create_jwt_token(global_view_user)},
    )

    # Assert that the response indicates failure (403 or 404)
    assert response.status_code == 404

    # Cleanup
    saved_search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_saved_search_by_user_with_access(create_standard_user):
    """
    Ensure that a standard user with access can successfully delete a saved search.

    This test verifies that the user who created the saved search can delete it by sending a DELETE request.
    Assertions:
        The response status code should be 200.
    """
    user = create_standard_user
    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=user,
    )
    response = client.delete(
        "/saved-searches/{}".format(search.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )

    assert response.status_code == 200

    # Cleanup
    if search:
        search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_delete_saved_search_by_user_without_access_fails(
    create_standard_user, create_secondary_standard_user
):
    """
    Ensure that a standard user without access cannot delete a saved search.

    This test verifies that a user cannot delete a saved search created by another user.
    Assertions:
        The response status code should be 404.
    """
    user_with_access = create_standard_user
    user_without_access = create_secondary_standard_user
    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=user_with_access,
    )
    response = client.delete(
        "/saved-searches/{}".format(search.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user_without_access)},
    )
    assert response.status_code == 404

    # Cleanup
    if search:
        search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_saved_searches_by_global_view_returns_none(create_global_view):
    """
    Ensure that a global view user cannot list saved searches.

    This test verifies that a global view user does not have access to view any saved searches.
    Assertions:
        The response status code should be 200.
        The response data should be an empty list.
    """
    global_view_user = create_global_view
    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
    )
    response = client.get(
        "/saved-searches",
        headers={"Authorization": "Bearer " + create_jwt_token(global_view_user)},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 0

    # Cleanup
    search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_list_saved_searches_by_user_only_gets_their_search(
    create_standard_user, create_secondary_standard_user
):
    """
    Ensure that a standard user can only list their own saved searches.

    This test verifies that a user only sees the saved searches they created.
    Assertions:
        The response status code should be 200.
        The response data should include only the searches created by the user.
    """
    primary_user = create_standard_user
    secondary_user = create_secondary_standard_user
    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=primary_user,
    )
    search2 = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=secondary_user,
    )
    response = client.get(
        "/saved-searches",
        headers={"Authorization": "Bearer " + create_jwt_token(primary_user)},
    )
    response_data = response.json()["result"]

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response_data[0]["id"] == str(search.id)

    # Cleanup
    search.delete()
    search2.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_saved_search_by_global_view_fails(create_global_view):
    """
    Ensure that a global view user cannot retrieve a saved search.

    This test verifies that a global view user cannot access a saved search by ID.
    Assertions:
        The response status code should be 404.
    """
    global_view_user = create_global_view
    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
    )
    response = client.get(
        "/saved-searches/{}".format(search.id),
        headers={"Authorization": "Bearer " + create_jwt_token(global_view_user)},
    )
    assert response.status_code == 404

    # Cleanup
    search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_saved_search_by_user_passes(create_standard_user):
    """
    Ensure that a standard user can retrieve their saved search by ID.

    This test verifies that a user can successfully retrieve a saved search they created.
    Assertions:
        The response status code should be 200.
        The response data should match the saved search's attributes.
    """
    user = create_standard_user
    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=user,
    )
    response = client.get(
        "/saved-searches/{}".format(search.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user)},
    )
    assert response.status_code == 200
    assert response.json()["name"] == search.name

    # Cleanup
    search.delete()


@pytest.mark.django_db(transaction=True, databases=["default", "mini_data_lake"])
def test_get_saved_search_by_different_user_fails(
    create_standard_user, create_secondary_standard_user
):
    """
    Ensure that a standard user cannot retrieve a saved search created by another user.

    This test verifies that access to saved searches is restricted to the creator.
    Assertions:
        The response status code should be 404.
    """
    user_with_access = create_standard_user
    user_without_access = create_secondary_standard_user
    search = SavedSearch.objects.create(
        name="test-{}".format(secrets.token_hex(4)),
        count=3,
        sort_direction="",
        sort_field="",
        search_term="",
        search_path="",
        filters=[],
        created_by=user_with_access,
    )
    response = client.get(
        "/saved-searches/{}".format(search.id),
        headers={"Authorization": "Bearer " + create_jwt_token(user_without_access)},
    )
    assert response.status_code == 404

    # Cleanup
    search.delete()
