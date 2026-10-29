"""Database models for the accounts application."""

# Standard Python Libraries
import uuid

# Third-Party Libraries
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Represent a WAS user with Django authentication and email preferences."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    email_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
