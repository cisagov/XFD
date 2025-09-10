"""User event logging decorator."""
# Standard Python Libraries
from datetime import datetime
import functools
import inspect
import json
import logging

# Third-Party Libraries
from asgiref.sync import sync_to_async
from xfd_mini_dl.models import Log, Organization, User

LOGGER = logging.getLogger(__name__)


async def maybe_async_call(func, *args, **kwargs):
    """Call a function and await it if it is a coroutine."""
    if inspect.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def log_action(action: str, message_or_cb=None):
    """
    Log an event after an endpoint is executed (decorator).

    :param action: A string identifier for the event (e.g., "USER ASSIGNED").
    :param message_or_cb: Either a dict or a callable that returns a dict payload.
           If a callable, it will be passed the endpoint's parameters (for example,
           current_user, response, and any other parameters) and should return a dict.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to extract the FastAPI Request and current_user if provided.
            current_user = kwargs.get("current_user", None)

            result = "success"
            response = None
            try:
                response = await func(*args, **kwargs)
            except Exception as e:
                result = "fail"
                raise e
            finally:
                try:
                    # Filter out keys that we are already passing explicitly.
                    filtered_kwargs = {
                        k: v
                        for k, v in kwargs.items()
                        if k not in ["current_user", "response"]
                    }

                    # Determine the payload to log.
                    if callable(message_or_cb):
                        payload = await maybe_async_call(
                            message_or_cb,
                            current_user=current_user,
                            response=response,
                            **filtered_kwargs
                        )
                    else:
                        payload = message_or_cb or {}

                    # Ensure payload is a dict and add a timestamp if missing.
                    if not isinstance(payload, dict):
                        payload = {}
                    if "timestamp" not in payload:
                        payload["timestamp"] = datetime.now().isoformat()

                    # Record the log entry using Django ORM.
                    await sync_to_async(Log.objects.create)(
                        payload=json.dumps(payload),
                        created_at=payload["timestamp"],
                        result=result,
                        event_type=action,
                    )
                except Exception as log_error:
                    # If logging fails, print a warning (or use your logging system).
                    LOGGER.warning("Logging error: %s", log_error)
            return response

        return wrapper

    return decorator


def get_organization_sync(org_id: str):
    """Get organization."""
    return Organization.objects.get(id=org_id)


def get_user_sync(user_id: str):
    """Get user."""
    return User.objects.get(id=user_id)
