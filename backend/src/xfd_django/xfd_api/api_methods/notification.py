"""/api-keys API logic."""

# Standard Python Libraries
import logging
import uuid

# Third-Party Libraries
from fastapi import HTTPException, status
from xfd_api.schema_models.notification import Notification as NotificationSchema
from xfd_mini_dl.models import Notification

LOGGER = logging.getLogger(__name__)

from ..auth import is_global_view_admin


def post(data, current_user):
    """POST LOGIC."""
    # Check if user is GlobalViewAdmin
    if not is_global_view_admin(current_user):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Ensure data is converted to dictionary
    data_dict = data.dict() if hasattr(data, "dict") else data

    # Create the record in the database using keyword arguments
    result = Notification.objects.create(**data_dict)

    # Return Serialized data from Schema
    return NotificationSchema.from_orm(result).dict()


def delete(notification_id, current_user):
    """DELETE LOGIC."""
    try:
        # Check if user is GlobalViewAdmin or has memberships
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Validate that key_id is a valid UUID
        uuid.UUID(notification_id)
        result = Notification.objects.get(id=notification_id)

        # Delete the Item
        result.delete()
        return {"status": "success", "message": "Item deleted successfully"}
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid id value"
        )
    except Notification.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )


def get_all():
    """GET All LOGIC."""
    try:
        # Get all objects from the database
        result = Notification.objects.all()

        LOGGER.info("Fetched notifications: %s", result)
        # Convert each object to Schema using from_orm
        return [NotificationSchema.from_orm(item) for item in result]

    except Exception as error:
        LOGGER.error("Error occurred while fetching all notifications: %s", error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_by_id(notification_id, current_user):
    """GET by id."""
    try:
        # Check if user is GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Find the item by its id
        result = Notification.objects.get(id=notification_id)

        LOGGER.info("Fetched notification: %s", result)
        # Convert the result to Schema using from_orm
        return NotificationSchema.from_orm(result)

    except HTTPException as http_exc:
        raise http_exc
    except Notification.DoesNotExist:
        raise HTTPException(status_code=404, detail="Item not found")
    except Exception as error:
        LOGGER.error("Error occurred while fetching notification by ID: %s", error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def update(notification_id, notification_data, current_user):
    """UPDATE by id."""
    try:
        # Check if user is GlobalViewAdmin
        if not is_global_view_admin(current_user):
            raise HTTPException(status_code=403, detail="Unauthorized")

        # Find the notification
        notification = Notification.objects.get(id=notification_id)

        # Update fields
        for key, value in notification_data.dict().items():
            setattr(notification, key, value)

        # Save changes
        notification.save()

        # Return updated notification
        return NotificationSchema.from_orm(notification)

    except HTTPException as http_exc:
        raise http_exc
    except Notification.DoesNotExist:
        raise HTTPException(status_code=404, detail="Notification not found")
    except Exception as error:
        LOGGER.error("Error occurred while updating notification: %s", error)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
