from utils.qualys_api_search.search_schedules import search_schedules
from utils.qualys_api_search.search_scans import search_scans
from utils.tracker_operations.create_tracker_items import create_tracker_items
from utils.tracker_operations.update_tracker import update_tracker


def main(delete_apps=True):
    """
    Main method for updating the tracker

    Parameters
    ----------
    delete_apps : bool, optional
        default true, use False for testing purposes
    """
    stakeholders = search_schedules()  # dictionary mapping tag to stakeholder object
    # dictionary mapping tag to list of scan slices
    scan_groups = search_scans(stakeholders)
    # list of tracker_item objects for populating the tracker
    tracker_items = create_tracker_items(scan_groups, stakeholders)
    update_tracker(tracker_items, delete_apps)  # populates excel spreadsheet


if __name__ == "__main__":
    main()
