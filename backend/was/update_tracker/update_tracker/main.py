from utils.qualys_api_search.search_schedules import search_schedules
from utils.qualys_api_search.search_scans import search_scans
from utils.tracker_operations.create_tracker_items import create_tracker_items
from utils.tracker_operations.update_tracker import update_tracker


def filter_stakeholders(stakeholders, stakeholder_tag=None):
    """Return all stakeholders or only the exact requested tag."""
    if stakeholder_tag is None:
        return stakeholders
    return {
        tag: stakeholder
        for tag, stakeholder in stakeholders.items()
        if tag == stakeholder_tag
    }


def main(delete_apps=True, stakeholder_tag=None):
    """
    Main method for updating the tracker

    Parameters
    ----------
    delete_apps : bool, optional
        default true, use False for testing purposes
    stakeholder_tag : str, optional
        exact stakeholder tag to process after schedule discovery
    """
    stakeholders = search_schedules(
        stakeholder_tag=stakeholder_tag
    )  # dictionary mapping tag to stakeholder object
    stakeholders = filter_stakeholders(stakeholders, stakeholder_tag)
    if not stakeholders:
        if stakeholder_tag:
            print(
                "No recent Qualys schedules found for stakeholder tag "
                "{}.".format(stakeholder_tag)
            )
        else:
            print("No recent Qualys schedules found.")
        return
    # dictionary mapping tag to list of scan slices
    scan_groups = search_scans(stakeholders)
    # list of tracker_item objects for populating the tracker
    tracker_items = create_tracker_items(scan_groups, stakeholders)
    update_tracker(tracker_items, delete_apps)  # populates excel spreadsheet


if __name__ == "__main__":
    main()
