from lxml.builder import E
from lxml.objectify import ObjectifiedElement, fromstring
from set_up import qgc, log_exception
from utils.qualys_api_search.search_schedules import INPUT_DATE
import sys

VERBOSE = True
RESULTS_LIMIT = 1000


def search_scans(stakeholders):
    """
    Searches the qualys api for all scan slices matching the criteria

    Parameters
    ----------
    stakeholders : dict
        dict mapping tag to stakeholder object

    Excepts
    ------
    AttributeError
        If there are no scans to search for

    Returns
    -------
    dict
        a reverse alphabetical dictionary mapping tag name to stakeholder object
    """
    print('searching scans...')
    scan_groups = {tag: [] for tag in stakeholders}
    tag_id_search_str = ",".join(str(stakeholder.tag_id)
                                 for stakeholder in stakeholders.values())
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
            E.Criteria(INPUT_DATE, field="launchedDate", operator="GREATER"),
            E.Criteria(tag_id_search_str,
                       field='webApp.tags.id', operator='IN')
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
        try:
            has_more = res_xml.hasMoreRecords
        except AttributeError as e:
            log_exception(exc=e, min_launch_date=INPUT_DATE,
                          tag_ids=tag_id_search_str)
            sys.exit("ERROR: No scans found. Review dailywas.log for query")
        # count = res_xml.count
        for scan in res_xml.data.WasScan:
            scan_name = scan.name.text
            for tag in scan_groups:
                if matches_tag(scan_name, tag, stakeholders):
                    scan_groups[tag].append(scan)
                    # print(f"Scans found for {tag}")
                    break
    # sort in reverse alphabetical order
    print("all scans found!")
    sorted_groups = dict(
        sorted(scan_groups.items(), key=lambda x: x[0], reverse=True))
    return sorted_groups


def matches_tag(scan_name, tag, stakeholders):
    """Check if scan_name matches the tag or stakeholder name pattern."""
    cadence = True
    tag_pattern = f" {tag} "
    stakeholder_pattern = f" {stakeholders[tag].name} "
    if stakeholders[tag].cadence == "DAILY" and "Monthly" in scan_name:
        cadence = False
    elif stakeholders[tag].cadence == "MONTHLY" and ("adhoc" in scan_name.lower() or "ad-hoc" in scan_name.lower() or "ad_hoc" in scan_name.lower()):
        cadence = False
    return tag_pattern in scan_name and stakeholder_pattern in scan_name and cadence