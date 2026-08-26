from utils.qualys_api_search.previous_nws import get_previous_nws
from data.special_reqs import KEEP_NWS
from data.search_customer_data import get_customer_data, get_dynamo_value


def create_multiscan(tag, stakeholder_name, scan_name, scan_list, search_date):
    """
    consoldiates individual slice scans into one status, result, list of webapps

    Parameters
    ----------
    tag : str
        stakeholder tag
    stakeholder_name : str
        full name of the stakeholder
    scan_name : str
        full name of the scan excluding slice #
    scan_list : list
        list of lxml slice scan objects from qualys api
    search_date : str
        string representation of most recent scan date as criteria to search for previous scans
        2024-07-26:T00:00:00Z

    Returns
    -------
    multi_scan_status : str
        consolidated multi scan status
    multi_scan_result : str
        consolidated multi scan result
    nws : bool
        true if multi scan includes inaccessible webapps (no web service)
    recent_nws_str : str
        html representation of recently inaccessible webapps (<br>url<br>url)
    removed_nws_str : str
        html representation of consecutively inaccessible webapps (<br>url)
    manual : str
        type of manual reporting required (static password, etc). empty if no manual reporting required
    """
    statuses = []
    results = []
    nws = False
    recent_nws = []
    removed_nws = []
    check_previous = True
    manual = ""
    fceb = False
    previous_urls = []
    qualys_errors = []

    adhoc = False
    adhoc_text = ['adhoc', 'ad-hoc', 'ad_hoc']
    if any(x in tag.lower() for x in adhoc_text):
        adhoc = True
    print(f"creating multiscan for {tag}")
    for scan in scan_list:
        url = scan.target.webApp.url.text
        status = scan.summary.resultsStatus.text
        if (status == "NO_WEB_SERVICE" or status == "NO_HOST_ALIVE") and tag not in KEEP_NWS:
            nws = True
            recent_nws.append(url)
            # WAVS - TAG - Customer Name - Cadence - Run #1
            monthly_run_number = int(scan_name.split(' Run #')[1].strip())
            if monthly_run_number > 1 and check_previous and not adhoc:
                previous_run = f"Run #{monthly_run_number - 1}"
                # search for containment of all 3 params
                previous_urls = get_previous_nws(
                    tag, stakeholder_name, previous_run, search_date)
                check_previous = False  # only need to check previous nws apps once per group
            if url in previous_urls:
                # store apps to remove due to consecutive nws scans
                removed_nws.append(url)
        if (status == "SCAN_INTERNAL_ERROR" or status == "SCAN_RESULTS_INVALID" or status == "PROCESSING"):
            qualys_errors.append(f"{url}<br>")
        statuses.append(scan.status.text)
        results.append(scan.summary.resultsStatus.text)
    # make multiscan status and result
    multi_scan_status, multi_scan_result = combined_status_and_result(
        statuses, results)
    # format nws/qualys error apps for html
    qualys_error_str = ''.join(qualys_errors)
    recent_nws_str = "<br>".join([""] + recent_nws)
    removed_nws_str = "<br>".join([""] + removed_nws)
    # check if scan requires manual reporting
    try:
        stakeholder = get_customer_data(tag)
        if get_dynamo_value(stakeholder, "Manual Report"):
            manual = "CHILD TAG / OTHER"
        if get_dynamo_value(stakeholder, "FCEB"):
            fceb = True
    except KeyError:
        print(
            f"WARNING: possible naming error / typos.  setting {tag} as manual")
        manual = "MANUAL"
    
    return multi_scan_status, multi_scan_result, nws, recent_nws_str, removed_nws_str, manual, fceb, qualys_error_str


def combined_status_and_result(statuses, results):
    """
    combines slice scan statuses and results into one status and result based on heirerarchy

    Parameters
    ----------
    statuses : list
        list of slice scan statuses
    results : list
        list of slice scan results

    Returns
    -------
    multi_scan_status : str
        consolidated status
    multi_scan_result : str
        consolidated result
    """
    multi_scan_status = 'Finished'
    multi_scan_result = 'Successful'
    if "RUNNING" in statuses:
        multi_scan_status = "Running"
        multi_scan_result = "Running"
    elif "ERROR" in statuses:
        index = statuses.index("ERROR")
        multi_scan_status = "Error"
        multi_scan_result = results[index]
    # elif "NO_HOST_ALIVE" in results:
    #     multi_scan_result = "No Host Alive"
    #     multi_scan_status = "Error"
    else:
        other_errors = [result for result in results if result not in ["SUCCESSFUL",
                                                                       "NO_WEB_SERVICE", "TIME_LIMIT_REACHED", "SERVICE_ERROR"]]
        if other_errors:
            multi_scan_result = "Scan Internal Error"
            multi_scan_status = "Error"
        elif "SERVICE_ERROR" in results:
            multi_scan_result = "Service Error"
        elif "NO_WEB_SERVICE" in results:
            multi_scan_result = "No Web Service"
        elif "TIME_LIMIT_REACHED" in results:
            multi_scan_result = "Time Limit Reached"
    return multi_scan_status, multi_scan_result
