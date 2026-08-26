from datetime import datetime, timezone
import pytz
from data.special_reqs import ASSIGNEES
from utils.tracker_operations.webapp_operations import webapp_count, delete_webapp
from data.search_customer_data import get_customer_data, get_dynamo_value
from data.update_customer_data import update_customer_data
from set_up import DAILY_REPORTS, dailyReportsTracker, dailyReportsFilePath

CURRENT_DAY = datetime.today().strftime('%m/%d/%y')
CURRENT_DAY = datetime.strptime(CURRENT_DAY, '%m/%d/%y')


def update_tracker(tracker_items, delete_apps):
    """
    updates the tracker excel file

    Parameters
    ----------
    tracker_items : list
        list of tracker_item objects
    delete_apps : bool
        default True, use False for testing purposes to avoid webapp deletion
    """
    item_count = 0
    assignee = 0
    apps_to_delete = []
    scans_per_assignee = len(tracker_items) / len(ASSIGNEES)
    DAILY_REPORTS.insert_rows(3, 2)
    for item in tracker_items:
        populate_row(item, assignee)
        if item.removed_nws and not item.fceb:
            for app in item.removed_nws.split("<br>"):
                if app:
                    apps_to_delete.append(app)
        item_count += 1
        if item_count >= (assignee + 1) * scans_per_assignee:
            assignee += 1
    DAILY_REPORTS.delete_rows(3)
    dailyReportsTracker.save(dailyReportsFilePath)
    if delete_apps:
        for webapp in apps_to_delete:
            delete_webapp(webapp)
    else:
        print("WEBAPP DELETION SET TO FALSE")
    # set off powerautomate flow
    # file = open(str(POWERA_FOLDER) + '/dailywas.txt', 'w')
    # file.write('tracker updated')
    # file.close()


def populate_row(item, assignee):
    """
    populates one row of the excel tracker file

    Parameters
    ----------
    item : tracker_item
        tracker_item object holding all necessary report info
    assignee : int
        index representing which analyst from the ASSIGNEES list will be responsible for the report
    """
    print(f"Adding {item.tag} to tracker")
    no_error = True
    DAILY_REPORTS['S3'] = int(item.schedule_id)
    try:
        stakeholder = get_customer_data(item.tag)
        if get_dynamo_value(stakeholder, "Report Password"):
            DAILY_REPORTS['R3'] = 'STATIC PASSWORD'
    except KeyError:
        print(
            f"WARNING: possible naming error / typos.  setting {item.tag} as manual")
        DAILY_REPORTS['G3'] = "MANUAL"
        no_error = False
    
    

    DAILY_REPORTS['A3'] = CURRENT_DAY
    DAILY_REPORTS['A3'].number_format = 'm/d/yy'
    DAILY_REPORTS['B3'] = item.tag
    DAILY_REPORTS['C3'] = item.scan_name
    # reverse order to match up letter groups
    DAILY_REPORTS['D3'] = ASSIGNEES[::-1][assignee]
    DAILY_REPORTS['E3'] = item.status
    DAILY_REPORTS['F3'] = item.result
    DAILY_REPORTS['G3'] = item.manual
    #
    # skip column H for confirmation of manual report delivery
    #
    DAILY_REPORTS['I3'] = convert_qualys_dt(item.launched_date)
    DAILY_REPORTS['J3'] = convert_qualys_dt(item.next_scan_date)
    try:
        # DAILY_REPORTS['K3'], DAILY_REPORTS['L3'], DAILY_REPORTS['M3'], DAILY_REPORTS['N3'] = get_customer_data(
        #     item.tag)
        tech_poc_email = get_dynamo_value(stakeholder, "Tech POC Email")
        distro_email = get_dynamo_value(stakeholder, "Distro Email")

        DAILY_REPORTS['K3'] = get_dynamo_value(stakeholder, "WAS Report POC")
        DAILY_REPORTS['L3'] = f"{tech_poc_email}; {distro_email}" if tech_poc_email and distro_email else tech_poc_email or distro_email
        DAILY_REPORTS['M3'] = get_dynamo_value(stakeholder, "Comments")
    except UnboundLocalError:
        print(
            f"WARNING: possible naming error / typos.  setting {item.tag} as manual")
        DAILY_REPORTS['G3'] = "MANUAL"
        no_error = False
    try:
        num_apps = webapp_count(item.tag)
    except AttributeError:
        num_apps = 0
        print(
            f"WARNING: No webapps for {item.tag}.  setting {item.tag} as manual")
        DAILY_REPORTS['G3'] = "MANUAL"
        no_error = False
    if item.nws:
        recent = len(item.recent_nws.split("<br>")) - 1
        removed = len(item.removed_nws.split("<br>")) - 1
        DAILY_REPORTS['N3'] = f"{num_apps}, {recent}, {removed}"
        if num_apps == removed:
            if item.fceb:
                DAILY_REPORTS['O3'] = 'FCEB All NWS'
            else:
                DAILY_REPORTS['O3'] = 'Deactivated'
                DAILY_REPORTS['G3'] = 'DEACTIVATE'
        elif num_apps == recent:
            if item.fceb:
                DAILY_REPORTS['O3'] = 'FCEB All NWS'
            else:
                DAILY_REPORTS['O3'] = 'All NWS'
        elif removed > 0:
            if item.fceb:
                DAILY_REPORTS['O3'] = 'FCEB Action Required'
            else:
                DAILY_REPORTS['O3'] = 'Targets Removed'
        else:
            if item.fceb:
                DAILY_REPORTS['O3'] = 'FCEB Action Required'
            else:
                DAILY_REPORTS['O3'] = 'Action Required'
    elif no_error and item.scan_name:
        DAILY_REPORTS['N3'] = num_apps
        DAILY_REPORTS['O3'] = 'Results'
    DAILY_REPORTS['P3'] = item.recent_nws
    DAILY_REPORTS['Q3'] = item.removed_nws
    DAILY_REPORTS['T3'] = item.qualys_errors
    DAILY_REPORTS.insert_rows(3)
    update_customer_data(item.tag, item.launched_date, item.next_scan_date, num_apps)

def convert_qualys_dt(scan_date):
    """
    converts time zone on qualys datetime strings

    Parameters
    ----------
    scan_date : str
        date in qualys format 2024-08-01T00:00:00Z

    Returns
    -------
    datestr : str
        subtracted 4 hours to account for qualys scanner timezone
        format 8/1/2024
    """
    scan_date = datetime.strptime(
        scan_date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    tz = pytz.timezone("US/Eastern")
    scan_date_tz = scan_date.astimezone(tz)
    datestr = scan_date_tz.strftime("%-m/%-d/%Y")
    return datestr
