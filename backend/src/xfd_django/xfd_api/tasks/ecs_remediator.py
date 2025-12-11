"""ECS remediation task."""
# Standard Python Libraries
import datetime
import logging
import os
from typing import Any, Dict, cast
import uuid

# Third-Party Libraries
import boto3
from botocore.exceptions import BotoCoreError, ClientError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")

# Logging
LOGGER = logging.getLogger(__name__)

ecs_client = boto3.client("ecs")
cloudwatch_client = boto3.client("cloudwatch")
sns_client = boto3.client("sns")

CUSTOM_METRIC_NAMESPACE = os.getenv("CUSTOM_METRIC_NAMESPACE", "Crossfeed/Remediation")
SNS_TOPIC_ARN = os.getenv("SNS_ALARMS_TOPIC_ARN")


def _get_environment_value(variable_name: str) -> str:
    value = os.getenv(variable_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {variable_name}")
    return value


def _extract_alarm_details(event: Dict[str, Any]) -> Dict[str, str]:
    """Get alarm details from event."""
    detail = event.get("detail", {})
    alarm_name = detail.get("alarmName", "unknown-alarm")
    state_value = detail.get("state", {}).get("value", "UNKNOWN")
    return {
        "alarm_name": alarm_name,
        "state_value": state_value,
    }


def _push_custom_metric(correlation_id: str, remediation_status: str) -> None:
    """Push custom metric at AWS."""
    timestamp = datetime.datetime.utcnow()
    try:
        cloudwatch_client.put_metric_data(
            Namespace=CUSTOM_METRIC_NAMESPACE,
            MetricData=[
                {
                    "MetricName": "ECSRemediationStatus",
                    "Dimensions": [
                        {"Name": "Project", "Value": _get_environment_value("PROJECT")},
                        {"Name": "Stage", "Value": _get_environment_value("STAGE")},
                        {"Name": "CorrelationId", "Value": correlation_id},
                    ],
                    "Timestamp": timestamp,
                    "Value": 1.0 if remediation_status in ("SUCCESS",) else 0.0,
                    "Unit": "Count",
                }
            ],
        )
    except (BotoCoreError, ClientError) as err:
        LOGGER.error(
            {
                "message": "Failed to publish custom metric",
                "error": str(err),
                "correlation_id": correlation_id,
            }
        )


def _send_sns_notification(topic_arn: str, subject: str, message: str) -> None:
    """Send SNS notification."""
    try:
        sns_client.publish(TopicArn=topic_arn, Subject=subject, Message=message)
    except (BotoCoreError, ClientError) as err:
        LOGGER.error(
            {
                "message": "Failed to send SNS notification",
                "error": str(err),
                "topic_arn": topic_arn,
            }
        )


def _restart_ecs_service(cluster: str, service: str) -> Dict[str, Any]:
    describe_resp = ecs_client.describe_services(cluster=cluster, services=[service])
    services = describe_resp.get("services", [])
    if not services:
        raise RuntimeError(f"ECS service {service} not found in cluster {cluster}.")
    service_desc = services[0]
    status = service_desc.get("status", "UNKNOWN")
    if status != "ACTIVE":
        raise RuntimeError(
            f"ECS service {service} in cluster {cluster} is not ACTIVE (status={status})."
        )

    update_resp = ecs_client.update_service(
        cluster=cluster, service=service, forceNewDeployment=True
    )
    return {
        "cluster": cluster,
        "service": service,
        "deployment_id": update_resp["service"]["deployments"][0]["id"],
        "desired_count": update_resp["service"]["desiredCount"],
        "status": update_resp["service"]["status"],
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler function."""
    correlation_id = str(uuid.uuid4())
    start_time = datetime.datetime.utcnow().isoformat() + "Z"
    alarm_details = _extract_alarm_details(event)
    cluster = _get_environment_value("ECS_CLUSTER_NAME")
    service = _get_environment_value("ECS_SERVICE_NAME")

    LOGGER.info(
        {
            "message": "Received alarm event",
            "alarm_details": alarm_details,
            "cluster": cluster,
            "service": service,
            "correlation_id": correlation_id,
            "timestamp": start_time,
        }
    )

    response_body: Dict[str, Any] = {
        "alarm_name": alarm_details["alarm_name"],
        "state_value": alarm_details["state_value"],
        "correlation_id": correlation_id,
        "start_time": start_time,
        "remediation_performed": False,
        "remediation_error": None,
        "ecs_update": None,
    }

    if alarm_details["state_value"] != "ALARM":
        LOGGER.info(
            {
                "message": "Alarm not in ALARM state — skipping remediation",
                "state_value": alarm_details["state_value"],
                "correlation_id": correlation_id,
            }
        )

        _push_custom_metric(correlation_id, "NO_ACTION")
        return response_body

    try:
        ecs_update_result = _restart_ecs_service(cluster, service)
        response_body["remediation_performed"] = True
        response_body["ecs_update"] = ecs_update_result
        LOGGER.info(
            {
                "message": "Successfully triggered ECS service redeployment",
                "ecs_update": ecs_update_result,
                "correlation_id": correlation_id,
            }
        )

        _push_custom_metric(correlation_id, "SUCCESS")
    except (BotoCoreError, ClientError, RuntimeError) as err:
        response_body["remediation_error"] = str(err)
        LOGGER.error(
            {
                "message": "ECS remediation failed",
                "error": str(err),
                "correlation_id": correlation_id,
            }
        )

        _push_custom_metric(correlation_id, "FAILURE")

        # Send SNS notification for failure
        subject = f"[{_get_environment_value('PROJECT')}-{_get_environment_value('STAGE')}] ECS remediation FAILED for {cluster}/{service}"
        message = (
            f"Remediation for ECS cluster '{cluster}', service '{service}' failed.\n"
            f"Alarm: {alarm_details['alarm_name']}\n"
            f"CorrelationId: {correlation_id}\n"
            f"Error: {err}"
        )
        _send_sns_notification(cast(str, SNS_TOPIC_ARN), subject, message)

    end_time = datetime.datetime.utcnow().isoformat() + "Z"
    response_body["end_time"] = end_time
    LOGGER.info(
        {
            "message": "Remediation execution completed",
            "correlation_id": correlation_id,
            "end_time": end_time,
        }
    )

    return response_body
