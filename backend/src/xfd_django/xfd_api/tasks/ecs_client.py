"""AWS Elastic Container Service Client."""

# Standard Python Libraries
from datetime import datetime, timezone
import json
import logging
import os

# Third-Party Libraries
import boto3

from ..schema_models.scan import SCAN_SCHEMA

LOGGER = logging.getLogger(__name__)


def to_snake_case(input_str):
    """Convert a string to snake_case."""
    return input_str.replace(" ", "-")


class ECSClient:
    """ECS Client."""

    def __init__(self, is_local=None):
        """Initialize."""
        # Determine if we're running locally or using ECS
        self.is_local = is_local or os.getenv("IS_OFFLINE") or os.getenv("IS_LOCAL")

        if self.is_local:
            # Third-Party Libraries
            import docker

            self.docker = docker.from_env()
        else:
            self.docker = None
        self.ecs = boto3.client("ecs") if not self.is_local else None
        self.cloudwatch_logs = boto3.client("logs") if not self.is_local else None

    def run_command(self, command_options):
        """Launch an ECS task or Docker container with the given command options."""
        scan_name = command_options["scanName"]
        scan_schema = SCAN_SCHEMA.get(scan_name, {})
        cpu = getattr(scan_schema, "cpu", None)
        memory = getattr(scan_schema, "memory", None)
        global_scan = getattr(scan_schema, "global_scan", False)
        count = command_options.get("count", 1)  # Number of containers to launch

        if self.is_local:
            LOGGER.info("In the local part of ecs run_command")
            tasks = []
            for i in range(count):
                try:
                    container_name = to_snake_case(
                        "crossfeed_worker_{global_str}_{scan}_{random}".format(
                            global_str="global" if global_scan else "local",
                            scan=scan_name,
                            random=int(os.urandom(4).hex(), 16),
                        )
                    )
                    container = self.docker.containers.run(
                        "crossfeed-worker",
                        name=container_name,
                        network_mode="backend",
                        mem_limit="4g",
                        environment={
                            "CROSSFEED_COMMAND_OPTIONS": json.dumps(command_options),
                            "CF_API_KEY": os.getenv("CF_API_KEY"),
                            "CHECKSUM_SALT": os.getenv("CHECKSUM_SALT"),
                            "PE_API_KEY": os.getenv("PE_API_KEY"),
                            "DB_DIALECT": os.getenv("DB_DIALECT"),
                            "DB_HOST": os.getenv("DB_HOST"),
                            "INTELX_KEY": os.getenv("INTELX_KEY"),
                            "IS_LOCAL": "true",
                            "IS_DMZ": os.getenv("IS_DMZ"),
                            "DB_PORT": os.getenv("DB_PORT"),
                            "DB_NAME": os.getenv("DB_NAME"),
                            "DB_USERNAME": os.getenv("DB_USERNAME"),
                            "DB_PASSWORD": os.getenv("DB_PASSWORD"),
                            "MDL_NAME": os.getenv("MDL_NAME"),
                            "MDL_SECONDARY_NAME": os.getenv("MDL_SECONDARY_NAME"),
                            "MDL_USERNAME": os.getenv("MDL_USERNAME"),
                            "MDL_PASSWORD": os.getenv("MDL_PASSWORD"),
                            "NIST_API_KEY": os.getenv("NIST_API_KEY"),
                            "PE_DB_NAME": os.getenv("PE_DB_NAME"),
                            "PE_DB_USERNAME": os.getenv("PE_DB_USERNAME"),
                            "PE_DB_PASSWORD": os.getenv("PE_DB_PASSWORD"),
                            "CENSYS_API_ID": os.getenv("CENSYS_API_ID"),
                            "CENSYS_API_SECRET": os.getenv("CENSYS_API_SECRET"),
                            "WORKER_USER_AGENT": os.getenv("WORKER_USER_AGENT"),
                            "SHODAN_API_KEY": command_options["SHODAN_API_KEY"],
                            "PE_SHODAN_API_KEYS": os.getenv("PE_SHODAN_API_KEYS"),
                            "QUALYS_USERNAME": os.getenv("QUALYS_USERNAME"),
                            "QUALYS_PASSWORD": os.getenv("QUALYS_PASSWORD"),
                            "WHOIS_XML_KEY": os.getenv("WHOIS_XML_KEY"),
                            "WHOIS_XML_THREAD_COUNT": os.getenv(
                                "WHOIS_XML_THREAD_COUNT"
                            ),
                            "WORKER_SIGNATURE_PUBLIC_KEY": os.getenv(
                                "WORKER_SIGNATURE_PUBLIC_KEY"
                            ),
                            "WORKER_SIGNATURE_PRIVATE_KEY": os.getenv(
                                "WORKER_SIGNATURE_PRIVATE_KEY"
                            ),
                            "ELASTICSEARCH_ENDPOINT": os.getenv(
                                "ELASTICSEARCH_ENDPOINT"
                            ),
                            "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
                            "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
                            "LG_API_KEY": os.getenv("LG_API_KEY"),
                            "LG_WORKSPACE_NAME": os.getenv("LG_WORKSPACE_NAME"),
                            "SERVICE_QUEUE_URL": os.getenv("QUEUE_URL", ""),
                            "DMZ_SYNC_ENDPOINT": os.getenv("DMZ_SYNC_ENDPOINT", ""),
                            "DMZ_API_KEY": os.getenv("DMZ_API_KEY", ""),
                            "QUEUE_URL": os.getenv("QUEUE_URL", ""),
                            "XPANSE_ORG_SYNC_BUCKET_NAME": os.getenv(
                                "XPANSE_ORG_SYNC_BUCKET_NAME"
                            ),
                            "XPANSE_API_KEY": os.getenv("XPANSE_API_KEY"),
                            "XPANSE_AUTH_ID": os.getenv("XPANSE_AUTH_ID"),
                            "VS_PULL_DATE_RANGE": os.getenv("VS_PULL_DATE_RANGE", "90"),
                        },
                        detach=True,
                    )
                    tasks.append({"taskArn": container.name})
                    LOGGER.info("Started local container: %s", container_name)
                except Exception as e:
                    LOGGER.error("Error starting local container %d: %s", i, e)
                    return {"tasks": tasks, "failures": [{"error": str(e)}]}
            return {"tasks": tasks, "failures": []}

        # Run the command on ECS (non-local)
        container_env = [
            {
                "name": "CROSSFEED_COMMAND_OPTIONS",
                "value": json.dumps(command_options),
            },
            {"name": "SERVICE_TYPE", "value": scan_name},
            {
                "name": "SERVICE_QUEUE_URL",
                "value": command_options.get("SERVICE_QUEUE_URL"),
            },
            {
                "name": "NODE_OPTIONS",
                "value": "--max_old_space_size={}".format(memory) if memory else "",
            },
            {
                "name": "SHODAN_API_KEY",
                "value": command_options.get("SHODAN_API_KEY") or "",
            },
        ]

        response = self.ecs.run_task(
            cluster=os.getenv("FARGATE_CLUSTER_NAME"),
            taskDefinition=os.getenv("FARGATE_TASK_DEFINITION_NAME"),
            networkConfiguration={
                "awsvpcConfiguration": {
                    "assignPublicIp": "ENABLED",
                    "securityGroups": [os.getenv("FARGATE_SG_ID")],
                    "subnets": [os.getenv("FARGATE_SUBNET_ID")],
                }
            },
            platformVersion="1.4.0",
            launchType="FARGATE",
            count=count,  # Pass the count here
            overrides={
                "cpu": cpu,
                "memory": memory,
                "containerOverrides": [
                    {
                        "name": "main",
                        "environment": container_env,
                    }
                ],
            },
        )
        return response

    def get_logs(self, fargate_task_arn):
        """Get logs for a specific Fargate or Docker task."""
        if self.is_local:
            # Retrieve logs from the local Docker container
            log_stream = self.docker.containers.get(fargate_task_arn).logs(
                stdout=True, stderr=True, timestamps=True
            )
            # Process and return the logs
            return "\n".join(line for line in log_stream.decode("utf-8").splitlines())
        else:
            log_stream_name = "worker/main/{}".format(fargate_task_arn.split("/")[-1])

            # Fetch logs from AWS CloudWatch
            response = self.cloudwatch_logs.get_log_events(
                logGroupName=os.getenv("FARGATE_LOG_GROUP_NAME"),
                logStreamName=log_stream_name,
                startFromHead=True,
            )

            # Process and format the logs
            events = response.get("events", [])
            if not events:
                return ""

            # Format the logs as "timestamp message"
            formatted_logs = "\n".join(
                "{} {}".format(
                    datetime.fromtimestamp(
                        event["timestamp"] / 1000, timezone.utc
                    ).isoformat(timespec="seconds"),
                    event["message"],
                )
                for event in events
            )
            return formatted_logs

    def get_num_tasks(self):
        """Retrieve the number of running tasks associated with the Fargate worker."""
        if self.is_local:
            containers = self.docker.containers.list(
                filters={"ancestor": "crossfeed-worker"}
            )
            return len(containers)
        tasks = self.ecs.list_tasks(
            cluster=os.getenv("FARGATE_CLUSTER_NAME"), launchType="FARGATE"
        )
        return len(tasks.get("taskArns", []))
