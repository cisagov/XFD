from set_up import CUSTOMER_DATA

from datetime import datetime, timezone
import time
from was_dynamodb.attribute import Attribute
from botocore.exceptions import ClientError


def update_customer_data(tag, last_scan, next_scan, app_count):
    # Parse the string into a datetime object
    last_scan_dt = datetime.strptime(last_scan, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    next_scan_dt = datetime.strptime(next_scan, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    # Convert the datetime object to a Unix timestamp (seconds since epoch)
    last_scan_timestamp = int(last_scan_dt.timestamp())
    next_scan_timestamp = int(next_scan_dt.timestamp())
    partition_key = Attribute("Tag", tag).to_dict()
    attributes = [
        Attribute("Next Scheduled", str(next_scan_timestamp)),
        Attribute("Last Scanned", str(last_scan_timestamp)),
        Attribute("# of Web Apps", str(app_count)),
        Attribute("# of Web Apps Last Updated", str(time.time().__floor__())),
    ]
    attributes_dict = {}
    for attribute in attributes:
        attributes_dict = attributes_dict | attribute.to_dict()
    try:
        CUSTOMER_DATA.update_item(partition_key, attributes_dict)
    except ClientError:
        print(f"WARNING: Unable to update scan dates / app count for {tag}")
