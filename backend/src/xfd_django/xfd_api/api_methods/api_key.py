"""/api-keys API logic."""

# Standard Python Libraries
from datetime import datetime
import hashlib
import secrets
import uuid

# Third-Party Libraries
from fastapi import HTTPException, status
from xfd_api.schema_models.api_key import ApiKey as ApiKeySchema
from xfd_mini_dl.models import ApiKey

from ..auth import is_global_view_admin


def post(current_user):
    """POST API logic for creating a new API key."""
    # Check if user is GlobalViewAdmin or has memberships
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Generate a random 16-byte API key
    key = secrets.token_hex(16)

    # Hash the API key
    hashed_key = hashlib.sha256(key.encode()).hexdigest()

    # Create ApiKey instance in the database
    api_key_instance = ApiKey.objects.create(
        id=uuid.uuid4(),
        hashed_key=hashed_key,
        last_four=key[-4:],
        user=current_user,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # Convert the Django model instance to Pydantic, excluding fields like hashedKey and user
    validated_data = ApiKeySchema.model_validate(api_key_instance).model_dump(
        exclude={"hashed_key", "user"}
    )

    # Add the actual API key to the response for initial display to the user
    validated_data["api_key"] = key

    return validated_data


def delete(api_key_id, current_user):
    """DELETE API LOGIC."""
    try:
        # Check if user is GlobalViewAdmin or has memberships
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Confirm id is a valid UUID
        uuid.UUID(api_key_id)

        # Delete by id
        api_key = ApiKey.objects.get(id=api_key_id)
        api_key.delete()

        # Delete Response TODO: confirm output
        return {"status": "success", "message": "API Key deleted successfully"}

    except ApiKey.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API Key not found"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid API Key ID"
        )


def get_all(current_user):
    """GET All API LOGIC."""
    try:
        # Check if user is GlobalViewAdmin or has memberships
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Get all ApiKey objects from the database
        api_keys = ApiKey.objects.all()

        # Return schema validated response
        validated_response = [
            ApiKeySchema.model_validate(item).model_dump(
                exclude={"hashed_key", "user_id"}
            )
            for item in api_keys
        ]

        return validated_response

    except HTTPException as http_exc:
        raise http_exc

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


def get_by_id(api_key_id, current_user):
    """GET API KEY by id."""
    try:
        # Check if user is GlobalViewAdmin or has memberships
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Confirm id is a valid UUID
        uuid.UUID(api_key_id)

        # Find the ApiKey by its ID
        api_key = ApiKey.objects.get(id=api_key_id)

        # Return validated output
        return ApiKeySchema.model_validate(obj=api_key).model_dump(
            exclude={"hashed_key", "user_id"}
        )

    except HTTPException as http_exc:
        raise http_exc

    except ApiKey.DoesNotExist:
        raise HTTPException(status_code=404, detail="API Key not found")

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
