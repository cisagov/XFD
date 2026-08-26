
from lxml.builder import E
from lxml.objectify import ObjectifiedElement, fromstring
from set_up import qgc, log_exception
import sys

RESULTS_LIMIT = 1000
VERBOSE = True


def get_previous_nws(tag, name, previous_run, search_date):
    """
    gets the urls of webapps that were inaccessible in the previous scan

    Parameters
    ----------
    tag : str
        stakeholder tag
    name : str
        stakeholder name
    previous_run : str
        str representation of the previous scan run number ("Run #1")
    search_date : str
        most recent scan launch date in qualys search criterai format (2024-07-26T00:00:00Z)

    Returns
    -------
    previous_nws : list
        list of webapp urls that were previously inaccessible
    """
    print(f"getting previous scan nws apps for {name}...")
    # print(previous_run, tag, name, search_date)
    previous_nws = []  # list to store nws apps from previous scan
    SEARCH_ENDPOINT = 'search/was/wasscan'
    offset: int = 1  # Qualys API indexes offset at 1
    offset_element = E.startFromOffset(str(offset))
    req = E.ServiceRequest(
        E.preferences(
            # E.verbose("true" if VERBOSE else "false"),
            E.limitResults(str(RESULTS_LIMIT)),
            offset_element,
        ),
        E.filters(
            E.Criteria(search_date, field='launchedDate', operator='LESSER'),
            E.Criteria(tag, field='name', operator='CONTAINS'),
            E.Criteria(name, field='name', operator='CONTAINS'),
            E.Criteria(previous_run, field='name', operator='CONTAINS')
        )
    )
    has_more: bool = True
    # count = RESULTS_LIMIT
    while has_more:
        # while count >= RESULTS_LIMIT:
        
        res_str: str = qgc.request(SEARCH_ENDPOINT, req, http_method="post")
        res_xml: ObjectifiedElement = fromstring(res_str.encode())
        offset += res_xml.count
        offset_element.text = str(offset)
        has_more = res_xml.hasMoreRecords
        # count = res_xml.count
        for scan in res_xml.data.WasScan:
            if scan.status == "ERROR":
                continue
            if scan.summary.resultsStatus == "NO_WEB_SERVICE":
                previous_nws.append(scan.target.webApp.url.text)
    print('previous nws apps found')
    return previous_nws
