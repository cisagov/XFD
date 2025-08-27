"""AWS Lambda Client."""

# Standard Python Libraries
import logging
import os

# Third-Party Libraries
import boto3

from .scheduler import handler as scheduler

LOGGER = logging.getLogger(__name__)


class LambdaClient:
    """Lambda client."""

    def __init__(self):
        """Initialize."""
        # Determine if running locally or not
        self.is_local = os.getenv("IS_OFFLINE") or os.getenv("IS_LOCAL")
        if not self.is_local:
            # Initialize Boto3 Lambda client only if not local
            self.lambda_client = boto3.client(
                "lambda", region_name=os.getenv("AWS_REGION", "us-east-1")
            )

    def run_command(self, name: str):
        """Invoke a lambda function with the given name."""
        LOGGER.info("Invoking lambda function: %s", name)
        if self.is_local:
            # If running locally, directly call the scheduler function
            scheduler({}, {})
            return {"status": 200, "message": ""}
        else:
            # Invoke the lambda function asynchronously
            response = self.lambda_client.invoke(
                FunctionName=name, InvocationType="Event", Payload=""
            )
            return response
