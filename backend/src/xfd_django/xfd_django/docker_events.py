"""Docker event listener."""
# Standard Python Libraries
import json
import logging
import time

# Third-Party Libraries
from django.conf import settings

LOGGER = logging.getLogger(__name__)

if settings.IS_LOCAL:
    # Third-Party Libraries
    from docker import DockerClient

# Import your updateScanTaskStatus handler
# Third-Party Libraries
from xfd_api.tasks.updateScanTaskStatus import handler as update_scan_task_status


def listen_for_docker_events():
    """Listen for Docker events."""
    try:
        if settings.IS_LOCAL:
            try:
                client = DockerClient.from_env()
                LOGGER.info("Listening for Docker events...")
            except Exception as e:
                LOGGER.error("Failed to connect to Docker: %s", e)
                return
        else:
            LOGGER.warning("Skipping Docker event listener because IS_LOCAL=False")
            return

        for event in client.events(decode=True):
            try:
                # Extract relevant event details
                status = event.get("status")
                actor = event.get("Actor", {})
                attributes = actor.get("Attributes", {})
                image_name = event.get("from")

                # Only process events related to 'crossfeed-worker'
                if image_name != "crossfeed-worker":
                    continue

                # Prepare the payload based on the event status
                payload = None
                if status == "start":
                    payload = {
                        "detail": {
                            "stopCode": "",
                            "stoppedReason": "",
                            "taskArn": attributes.get("name", ""),
                            "lastStatus": "RUNNING",
                            "containers": [{}],
                        }
                    }
                elif status == "die":
                    payload = {
                        "detail": {
                            "stopCode": "EssentialContainerExited",
                            "stoppedReason": "Essential container in task exited",
                            "taskArn": attributes.get("name", ""),
                            "lastStatus": "STOPPED",
                            "containers": [
                                {
                                    "exitCode": int(attributes.get("exitCode", 1)),
                                }
                            ],
                        }
                    }
                else:
                    continue

                # Log and process the event
                LOGGER.info(
                    "Processing Docker event: %s", json.dumps(payload, indent=2)
                )
                # Retry logic to find the ScanTask before updating
                for attempt in range(3):
                    response = update_scan_task_status(payload, None)
                    if response.get("status_code") == 200:
                        break  # Success, exit loop
                    time.sleep(1)  # Wait before retrying

            except Exception as e:
                LOGGER.error("Error processing Docker event: %s", e)

    except Exception as e:
        LOGGER.error("Error connecting to Docker: %s", e)
