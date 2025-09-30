"""Django middleware."""
# Standard Python Libraries
from datetime import datetime
import json
import logging

# Third-Party Libraries
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware."""

    def __init__(self, app):
        """Initialize logger."""
        super().__init__(app)
        # Always use the logger configured in settings.py
        self.logger = logging.getLogger("fastapi.requests")

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
            "aws_request_id": request_id,
        }
        self.logger.info(json.dumps(start_log))
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
            "aws_request_id": request_id,
        }
        self.logger.info(json.dumps(end_log))

        return response
