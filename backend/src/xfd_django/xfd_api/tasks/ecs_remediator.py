import json
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError


ecs_client = boto3.client("ecs")


def _get_environment_value(variable_name: str) -> str:
    """
    Retrieve a required environment variable.

    Parameters
    ----------
    variable_name : str
        Name of the environment variable to retrieve.

    Returns
    -------
    str
        Value of the environment variable.

    Raises
    ------
    RuntimeError
        If the environment variable is not set.
    """
    variable_value = os.getenv(variable_name)
    if not variable_value:
        raise RuntimeError(f"Missing required environment variable: {variable_name}")
    return variable_value


def _extract_alarm_details(cloudwatch_event: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract alarm details from a CloudWatch Alarm State Change event.

    Parameters
    ----------
    cloudwatch_event : Dict[str, Any]
        EventBridge payload for the CloudWatch Alarm State Change.

    Returns
    -------
    Dict[str, str]
        Dictionary with alarm name and state value.
    """
    detail = cloudwatch_event.get("detail", {})
    alarm_name = detail.get("alarmName", "unknown-alarm")
    state = detail.get("state", {})
    state_value = state.get("value", "UNKNOWN")

    return {
        "alarm_name": alarm_name,
        "state_value": state_value,
    }


def _restart_ecs_service() -> Dict[str, Any]:
    """
    Trigger a new deployment for the configured ECS service.

    This is a safe way to recycle tasks and pull the latest
    task definition without manually stopping tasks.

    Returns
    -------
    Dict[str, Any]
        Structured result that describes the update operation.

    Raises
    ------
    botocore.exceptions.BotoCoreError
        If a low level AWS error occurs.
    botocore.exceptions.ClientError
        If ECS rejects the API call.
    """
    ecs_cluster_name = _get_environment_value("ECS_CLUSTER_NAME")
    ecs_service_name = _get_environment_value("ECS_SERVICE_NAME")

    describe_response = ecs_client.describe_services(
        cluster=ecs_cluster_name,
        services=[ecs_service_name],
    )

    services = describe_response.get("services", [])
    if not services:
        raise RuntimeError(
            f"ECS service {ecs_service_name} not found in cluster {ecs_cluster_name}."
        )

    service_description = services[0]
    service_status = service_description.get("status", "UNKNOWN")

    if service_status != "ACTIVE":
        raise RuntimeError(
            f"ECS service {ecs_service_name} in cluster {ecs_cluster_name} is not ACTIVE "
            f"(current status: {service_status})."
        )

    update_response = ecs_client.update_service(
        cluster=ecs_cluster_name,
        service=ecs_service_name,
        forceNewDeployment=True,
    )

    result = {
        "cluster": ecs_cluster_name,
        "service": ecs_service_name,
        "deployment_id": update_response["service"]["deployments"][0]["id"],
        "desired_count": update_response["service"]["desiredCount"],
        "status": update_response["service"]["status"],
    }
    return result


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Entry point for the ECS remediation Lambda.

    This handler is invoked by an EventBridge rule that listens for
    CloudWatch Alarm State Change events. When the configured API
    error rate alarm enters the ALARM state, this function triggers
    a new deployment of the ECS worker service to recycle tasks.

    Parameters
    ----------
    event : Dict[str, Any]
        EventBridge event payload.
    context : Any
        Lambda context object provided by AWS. This parameter is
        included for completeness even though it is not used.

    Returns
    -------
    Dict[str, Any]
        Structured response describing the remediation action taken.
    """
    alarm_details = _extract_alarm_details(event)
    alarm_name = alarm_details["alarm_name"]
    state_value = alarm_details["state_value"]

    response_body: Dict[str, Any] = {
        "alarm_name": alarm_name,
        "state_value": state_value,
        "remediation_performed": False,
        "remediation_error": None,
        "ecs_update": None,
    }

    print(json.dumps({"message": "Received alarm event", "details": alarm_details}))

    if state_value != "ALARM":
        print(
            json.dumps(
                {
                    "message": "Ignoring event because state is not ALARM.",
                    "state_value": state_value,
                }
            )
        )
        return response_body

    try:
        ecs_update_result = _restart_ecs_service()
        response_body["remediation_performed"] = True
        response_body["ecs_update"] = ecs_update_result
        print(
            json.dumps(
                {
                    "message": "Successfully triggered ECS service redeployment.",
                    "ecs_update": ecs_update_result,
                }
            )
        )
    except (BotoCoreError, ClientError, RuntimeError) as remediation_error:
        response_body["remediation_error"] = str(remediation_error)
        print(
            json.dumps(
                {
                    "message": "ECS remediation failed.",
                    "error": str(remediation_error),
                }
            )
        )

    return response_body
