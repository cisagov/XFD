"""UUID Helpers."""
# Standard Python Libraries
import uuid


def is_valid_uuid(val: str) -> bool:
    """Check if the given string is a valid UUID."""
    try:
        uuid_obj = uuid.UUID(val)
        # TODO: Uncomment to re-enable v4 uuid checks
        # uuid_obj = uuid.UUID(val, version=4)
    except ValueError:
        return False
    return str(uuid_obj) == val
