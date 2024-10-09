"""/api-keys API logic"""

# Standard Python Libraries
import uuid

# Third-Party Libraries
from fastapi import HTTPException, status
from xfd_api.models import Notification
from xfd_api.schema_models.notification import Notification as NotificationSchema


def post(data, current_user):
    """POST LOGIC"""
    data.extend(id=uuid.uuid4())
    # Create the record in the database
    result = Notification.objects.create(data)

    # Return Serialized data from Schema
    return NotificationSchema.from_orm(result).dict()


def delete(id, current_user):
    """DELETE LOGIC"""
    try:
        # Validate that key_id is a valid UUID
        uuid.UUID(id)
        result = Notification.objects.get(id=id, userId=current_user)

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


def get_all(current_user):
    """GET All LOGIC"""
    try:
        # Get all objects from the database
        result = Notification.objects.all()

        # Convert each object to Schema using from_orm
        return [NotificationSchema.from_orm(item) for item in result]

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


def get_by_id(id, current_user):
    """GET by id"""
    try:
        # Find the item by its id
        result = Notification.objects.get(id=id)

        # Convert the result to Schema using from_orm
        return NotificationSchema.from_orm(result)

    except Notification.DoesNotExist:
        raise HTTPException(status_code=404, detail="Item not found")
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


def get_508_banner(current_user):
    """GET 508 banner."""
    # TODO: Adding placeholder until we determine if we still need this.
    # Remove logic if no longer needed or update to actual return object.
    try:
        # Get the 508 banner from the DB
        result = ""

        # Format/Return Banner
        return result

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
