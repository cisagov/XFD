from models.tracker_item import tracker_item
from utils.tracker_operations.create_multiscan import create_multiscan
from datetime import datetime
from set_up import log_exception
from requests import HTTPError


def create_tracker_items(scan_groups, stakeholders):
    """_summary_

    Parameters
    ----------
    scan_groups : dict
        mapping of tag to list of lxml slice scan objects
    stakeholders : dict
        mapping of tag to stakeholder object

    Returns
    -------
    tracker_list : list
        list of tracker_item objects
    """
    tracker_list = []
    for tag in scan_groups.keys():
        stakeholder_name = stakeholders[tag].name
        next_scan_date = stakeholders[tag].next_scan_date
        launched_date = stakeholders[tag].launched_date
        schedule_id = stakeholders[tag].schedule_id
        try:
            scan_name = scan_groups[tag][0].name.text.split(' Slice')[0]
            status, result, nws, recent_nws, removed_nws, manual, fceb, qualys_errors = create_multiscan(
                tag,
                stakeholder_name,
                scan_name,
                scan_groups[tag],
                launched_date
            )
            tracker_list.append(
                tracker_item(
                    tag,
                    scan_name,
                    status,
                    result,
                    launched_date,
                    next_scan_date,
                    nws,
                    recent_nws,
                    removed_nws,
                    manual,
                    fceb,
                    schedule_id,
                    qualys_errors
                )
            )
        except (AttributeError, IndexError, HTTPError) as e:
            log_exception(exc=e, tag=tag)
            print(
                f"WARNING: error creating tracker item. marking {tag} as manual")
            tracker_list.append(tracker_item(
                tag,
                "",
                "",
                "",
                launched_date,
                next_scan_date,
                False,
                "",
                "",
                'MANUAL',
                False,
                schedule_id,
                ""
            )
            )
    return tracker_list