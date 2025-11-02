"""Scan execution."""
# Standard Python Libraries
import json
import logging

# Third-Party Libraries
from django.core.management.base import BaseCommand
import pika  # For RabbitMQ
from xfd_api.tasks.scanExecution import handler as scan_execution

# Configure logging
LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    """Command."""

    help = "Run local scan execution and send messages to RabbitMQ"

    def add_arguments(self, parser):
        """Add arguments."""
        parser.add_argument(
            "--scan-type", type=str, required=True, help="Type of scan to execute."
        )
        parser.add_argument(
            "--desired-count", type=int, default=1, help="Number of scans to run."
        )
        parser.add_argument(
            "--api-key-list", type=str, default="", help="Comma-separated API keys."
        )
        parser.add_argument(
            "--org-list", type=str, nargs="+", help="List of organizations."
        )
        parser.add_argument("--queue", type=str, help="RabbitMQ queue name.")

    def handle(self, *args, **options):
        """Handle method."""
        scan_type = options["scan_type"]
        desired_count = options["desired_count"]
        api_key_list = options["api_key_list"]
        org_list = options.get("org_list", [])
        queue = options.get("queue", "staging-{}-queue".format(scan_type))

        if not org_list:
            self.stdout.write(self.style.ERROR("Organization list cannot be empty."))
            return

        # Send messages to RabbitMQ queue
        for org in org_list:
            message = {"scriptType": scan_type, "org": org}
            self.send_message_to_queue(message, queue)

        # Run the local scan execution
        self.local_scan_execution(scan_type, desired_count, api_key_list)

    @staticmethod
    def send_message_to_queue(message, queue):
        """Send message to queue."""
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="rabbitmq")
            )
            channel = connection.channel()

            # Declare the queue
            channel.queue_declare(queue=queue, durable=True)

            # Send the message to the queue
            channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2
                ),  # Make message persistent
            )

            LOGGER.info("Message sent: %s", message)

            # Close the connection
            connection.close()
        except Exception as e:
            LOGGER.error("Error sending message to queue %s: %s", queue, e)

    @staticmethod
    def local_scan_execution(scan_type, desired_count, api_key_list=""):
        """Run the scan execution handler locally."""
        LOGGER.info("Starting local scan execution...")
        payload = {
            "scanType": scan_type,
            "desiredCount": desired_count,
            "apiKeyList": api_key_list,
        }
        scan_execution(payload, {})
