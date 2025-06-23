"""Django middleware."""
# Standard Python Libraries
from datetime import datetime
import json

# Third-Party Libraries
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from xfd_api.logger import LOGGER


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware."""

    def __init__(self, app):
        """Initialize logger."""
        super().__init__(app)
        self.logger = LOGGER.getChild("middleware.request")

    async def dispatch(self, request: Request, call_next):
        """Dispatch logger."""
        # Extract request details
        method = request.method
        protocol = request.url.scheme
        original_url = str(request.url)
        path = request.url.path
        headers = dict(request.headers)

        # Retrieve request ID
        aws_context = request.scope.get("aws.context", None)
        request_id = (
            getattr(aws_context, "aws_request_id", "undefined")
            if aws_context
            else "undefined"
        )

        # Default to "undefined" for userEmail if not provided
        user_email = (
            request.state.user_email
            if hasattr(request.state, "user_email")
            else "undefined"
        )

        # Log the initial request
        start_log = {
            "httpMethod": method,
            "protocol": protocol,
            "originalURL": original_url,
            "path": path,
            "status_code": None,  # Status is not known at this point
            "headers": headers,
            "userEmail": user_email,
        }
        self.logger.info(
            "INFO RequestId: %s %sZ Request Info: %s",
            request_id,
            datetime.utcnow().isoformat(),
            json.dumps(start_log),
        )
        # Process the request and capture the response
        start_time = datetime.utcnow()
        response = await call_next(request)
        end_time = datetime.utcnow()

        # Update userEmail after endpoint execution if it was set
        user_email = (
            request.state.user_email
            if hasattr(request.state, "user_email")
            else user_email
        )

        # Log the completed request
        end_log = {
            "httpMethod": method,
            "protocol": protocol,
            "originalURL": original_url,
            "path": path,
            "status_code": response.status_code,
            "headers": headers,
            "userEmail": user_email,
            "durationMs": round(
                (end_time - start_time).total_seconds() * 1000, 2
            ),  # Response time in ms
        }
        self.logger.info(
            "INFO RequestId: %s %sZ Request Info: %s",
            request_id,
            end_time.isoformat(),
            json.dumps(end_log),
        )

        return response
