"""Serializers to support user event logging."""
# Standard Python Libraries
from datetime import datetime, timezone
import json

# Third-Party Libraries
from xfd_mini_dl.models import Organization, User  # Adjust the import path as needed


def format_datetime(dt: datetime) -> str:
    """Format a datetime as an ISO 8601 UTC string with a trailing 'Z'."""
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def serialize_user(user: User) -> dict:
    """Serialize a User instance to a dictionary with camelCase keys."""
    return {
        "id": str(user.id),
        "cognito_id": user.cognito_id,
        "okta_id": user.okta_id,
        "login_gov_id": user.login_gov_id,
        "created_at": format_datetime(user.created_at),
        "updated_at": format_datetime(user.updated_at),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "email": user.email,
        "invite_pending": user.invite_pending,
        "login_blocked_by_maintenance": user.login_blocked_by_maintenance,
        "accepted_terms_version": user.accepted_terms_version,
        "user_type": user.user_type,
        "region_id": user.region_id,
        "state": user.state,
    }


def serialize_organization(org: Organization) -> dict:
    """
    Serialize an Organization instance to a dictionary with camelCase keys.

    Note: The pending_domains field is stored as TEXT but represents a JSON array.
    """
    try:
        pending = json.loads(org.pending_domains) if org.pending_domains else []
    except (json.JSONDecodeError, TypeError):
        pending = []
    return {
        "id": str(org.id),
        "created_at": format_datetime(org.created_at),
        "updated_at": format_datetime(org.updated_at),
        "acronym": org.acronym,
        "name": org.name,
        "root_domains": org.root_domains,
        "ip_blocks": org.ip_blocks,
        "is_passive": org.is_passive,
        "pending_domains": pending,
        "country": org.country,
        "state": org.state,
        "region_id": org.region_id,
        "state_fips": org.state_fips,
        "state_name": org.state_name,
        "county": org.county,
        "county_fips": org.county_fips,
        "type": org.type,
    }


def serialize_role(role) -> dict:
    """
    Serialize a Role instance to a dictionary.

    Adjust fields as needed.
    """
    return {
        "id": str(role.id),
        "role": role.role,
        "approved": role.approved,
        "user": serialize_user(role.user) if role.user else None,
        "created_at": format_datetime(role.created_at),
        "updated_at": format_datetime(role.updated_at),
    }
