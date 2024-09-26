"""AWS Elastic Container Service Client."""

# cisagov Libraries
from ..schema_models.scan import SCAN_SCHEMA

# Standard Python Libraries
import json
import os

# Third-Party Libraries
import boto3
import docker


def to_snake_case(input_str):
    """Converts a string to snake_case."""
    return input_str.replace(' ', '-')


class ECSClient:
    def __init__(self, is_local=None):
        """Initialize."""
        # Determine if we're running locally or using ECS
        self.is_local = is_local or os.getenv('IS_OFFLINE') or os.getenv('IS_LOCAL')
        self.docker = docker.from_env() if self.is_local else None
        self.ecs = boto3.client('ecs') if not self.is_local else None
        self.cloudwatch_logs = boto3.client('logs') if not self.is_local else None

    async def run_command(self, command_options):
        """Launches an ECS task or Docker container with the given command options."""
        scan_id = command_options['scanId']
        scan_name = command_options['scanName']
        num_chunks = command_options.get('numChunks')
        chunk_number = command_options.get('chunkNumber')
        scan_schema = SCAN_SCHEMA.get(scan_name, {})
        cpu = getattr(scan_schema, 'cpu', None)
        memory = getattr(scan_schema, 'memory', None)
        global_scan = getattr(scan_schema, 'global_scan', False)
        # These properties are not specified when creating a ScanTask (as a single ScanTask
        # can correspond to multiple organizations), but they are input into the the
        # specific task function that runs per organization.
        organization_id = command_options.get('organizationId')
        organization_name = command_options.get('organizationName')


        if self.is_local:
            # Run the command in a local Docker container
            try:
                container_name = to_snake_case(
                    f"crossfeed_worker_{'global' if global_scan else organization_name}_{scan_name}_{int(os.urandom(4).hex(), 16)}"
                )
                container = self.docker.containers.run(
                    'crossfeed-worker',
                    name=container_name,
                    network_mode='xfd_backend',
                    mem_limit='4g',
                    environment={
                        'CROSSFEED_COMMAND_OPTIONS': json.dumps(command_options),
                        'CF_API_KEY': os.getenv('CF_API_KEY'),
                        'PE_API_KEY': os.getenv('PE_API_KEY'),
                        'DB_DIALECT': os.getenv('DB_DIALECT'),
                        'DB_HOST': os.getenv('DB_HOST'),
                        'IS_LOCAL': 'true',
                        'DB_PORT': os.getenv('DB_PORT'),
                        'DB_NAME': os.getenv('DB_NAME'),
                        'DB_USERNAME': os.getenv('DB_USERNAME'),
                        'DB_PASSWORD': os.getenv('DB_PASSWORD'),
                        'MDL_NAME': os.getenv('MDL_NAME'),
                        'MDL_USERNAME': os.getenv('MDL_USERNAME'),
                        'MDL_PASSWORD': os.getenv('MDL_PASSWORD'),
                        'MI_ACCOUNT_NAME': os.getenv('MI_ACCOUNT_NAME'),
                        'MI_PASSWORD': os.getenv('MI_PASSWORD'),
                        'PE_DB_NAME': os.getenv('PE_DB_NAME'),
                        'PE_DB_USERNAME': os.getenv('PE_DB_USERNAME'),
                        'PE_DB_PASSWORD': os.getenv('PE_DB_PASSWORD'),
                        'CENSYS_API_ID': os.getenv('CENSYS_API_ID'),
                        'CENSYS_API_SECRET': os.getenv('CENSYS_API_SECRET'),
                        'WORKER_USER_AGENT': os.getenv('WORKER_USER_AGENT'),
                        'SHODAN_API_KEY': os.getenv('SHODAN_API_KEY'),
                        'SIXGILL_CLIENT_ID': os.getenv('SIXGILL_CLIENT_ID'),
                        'SIXGILL_CLIENT_SECRET': os.getenv('SIXGILL_CLIENT_SECRET'),
                        'PE_SHODAN_API_KEYS': os.getenv('PE_SHODAN_API_KEYS'),
                        'WORKER_SIGNATURE_PUBLIC_KEY': os.getenv('WORKER_SIGNATURE_PUBLIC_KEY'),
                        'WORKER_SIGNATURE_PRIVATE_KEY': os.getenv('WORKER_SIGNATURE_PRIVATE_KEY'),
                        'ELASTICSEARCH_ENDPOINT': os.getenv('ELASTICSEARCH_ENDPOINT'),
                        'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID'),
                        'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY'),
                        'LG_API_KEY': os.getenv('LG_API_KEY'),
                        'LG_WORKSPACE_NAME': os.getenv('LG_WORKSPACE_NAME')
                    },
                    detach=True
                )
                return {
                    'tasks': [{'taskArn': container.name}],
                    'failures': []
                }
            except Exception as e:
                print(e)
                return {
                    'tasks': [],
                    'failures': [{}]
                }

        # Run the command on ECS
        tags = [
            {'key': 'scanId', 'value': scan_id},
            {'key': 'scanName', 'value': scan_name}
        ]
        if organization_name and organization_id:
            tags.append({'key': 'organizationId', 'value': organization_id})
            tags.append({'key': 'organizationName', 'value': organization_name})
        if num_chunks is not None and chunk_number is not None:
            tags.append({'key': 'numChunks', 'value': str(num_chunks)})
            tags.append({'key': 'chunkNumber', 'value': str(chunk_number)})

        response = self.ecs.run_task(
            cluster=os.getenv('FARGATE_CLUSTER_NAME'),
            taskDefinition=os.getenv('FARGATE_TASK_DEFINITION_NAME'),
            networkConfiguration={
                'awsvpcConfiguration': {
                    'assignPublicIp': 'ENABLED',
                    'securityGroups': [os.getenv('FARGATE_SG_ID')],
                    'subnets': [os.getenv('FARGATE_SUBNET_ID')]
                }
            },
            platformVersion='1.4.0',
            launchType='FARGATE',
            overrides={
                'cpu': cpu,
                'memory': memory,
                'containerOverrides': [
                    {
                        'name': 'main',  # Name from task definition
                        'environment': [
                            {
                                'name': 'CROSSFEED_COMMAND_OPTIONS',
                                'value': json.dumps(command_options)
                            },
                            {
                                'name': 'NODE_OPTIONS',
                                'value': f"--max_old_space_size={memory}" if memory else ''
                            }
                        ]
                    }
                ]
            }
        )
        return response

    async def get_logs(self, fargate_task_arn):
        """Gets logs for a specific Fargate or Docker task."""
        if self.is_local:
            log_stream = self.docker.containers.get(fargate_task_arn).logs(stdout=True, stderr=True, timestamps=True)
            return ''.join(line[8:] for line in log_stream.split('\n'))
        else:
            log_stream_name = f"worker/main/{fargate_task_arn.split('/')[-1]}"
            response = self.cloudwatch_logs.get_log_events(
                logGroupName=os.getenv('FARGATE_LOG_GROUP_NAME'),
                logStreamName=log_stream_name,
                startFromHead=True
            )
            events = response['events']
            return '\n'.join(f"{event['timestamp']} {event['message']}" for event in events)

    async def get_num_tasks(self):
        """Retrieves the number of running tasks associated with the Fargate worker."""
        if self.is_local:
            containers = self.docker.containers.list(filters={'ancestor': 'crossfeed-worker'})
            return len(containers)
        tasks = self.ecs.list_tasks(
            cluster=os.getenv('FARGATE_CLUSTER_NAME'),
            launchType='FARGATE'
        )
        return len(tasks.get('taskArns', []))
