"""AWS Lambda Client."""

# cisagov Libraries
from .scheduler import handler as scheduler

# Standard Python Libraries
import os

# Third-Party Libraries
import boto3


class LambdaClient:
    def __init__(self):
        """Initialize."""
        # Determine if running locally or not
        self.is_local = os.getenv('IS_OFFLINE') or os.getenv('IS_LOCAL')
        if not self.is_local:
            # Initialize Boto3 Lambda client only if not local
            self.lambda_client = boto3.client('lambda', region_name=os.getenv('AWS_REGION', 'us-east-1'))

    async def run_command(self, name: str):
        """Invokes a lambda function with the given name."""

        print(f"Invoking lambda function: {name}")
        if self.is_local:
            # If running locally, directly call the scheduler function
            await scheduler({})
            return {"status": 202, "message": ""}
        else:
            # Invoke the lambda function asynchronously
            response = self.lambda_client.invoke(
                FunctionName=name,
                InvocationType='Event',
                Payload=''
            )
            return response
