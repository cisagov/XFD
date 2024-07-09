"""
A simple FastAPI application with a healthcheck endpoint, designed to run on AWS Lambda using the Mangum adapter.

Third-Party Libraries:
- fastapi: A modern, fast (high-performance), web framework for building APIs with Python 3.6+ based on standard Python type hints.
- mangum: An adapter for using ASGI applications with AWS Lambda & API Gateway.

This application includes:
- A single healthcheck endpoint (`/healthcheck`) that returns a JSON response with the status of the application.

Example usage:
1. Deploy this application to AWS Lambda using a serverless framework.
2. Access the healthcheck endpoint via the deployed API Gateway URL to verify the service is running.

Dependencies:
- fastapi==0.111.0
- mangum==0.17.0
- uvicorn==0.30.1 (for local development)
"""

# Third-Party Libraries
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()


# Healthcheck endpoint
@app.get("/healthcheck")
async def healthcheck():
    """
    Healthcheck endpoint.

    Returns:
        dict: A dictionary containing the health status of the application.
    """
    return {"status": "ok"}


handler = Mangum(app)
