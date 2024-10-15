# Third-Party Libraries
from django.core.management import call_command
import pytest


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    with django_db_blocker.unblock():
        call_command("migrate")  # Apply migrations before running the tests
