from set_up import qgc
from lxml.builder import E
from lxml.objectify import ObjectifiedElement, fromstring
from regex import sub
import re

VERBOSE = True
RESULTS_LIMIT = '1'  # should only be 1 active reoccuring shcedule per tag


def make_stakeholder_info(schedule_name):
    """
    parses/cleans qualys schedule name to handle typos while retrieving tag and customer name

    Parameters
    ----------
    schedule_name : str
        name of the schedule in qualys

    Returns
    -------
    tag : str
        tag / shortname for the stakeholder
    customer_name : str
        full organization name for the stakeholder
    """
    schedule_name = sub(r'\p{Pd}+', '-', schedule_name)
    schedule_name.replace('--', '-')
    schedule_name.replace("  ", " ")
    tag = schedule_name.split(" - ")[1]
    customer_name = schedule_name.split(" - ")[2]
    return tag, customer_name


def nextdate_for_adhoc(tag, name):
    """
    gets the next scan date for an adhoc scan that may have a TAG_ADHOC tag

    Parameters
    ----------
    tag : str
        tag for the adhoc scan
    name : str
        stakeholder name

    Returns
    -------
    next scan date : str
        str representation of the qualys format for next scan date of the main schedule
    """
    print(f"adhoc scan found: {tag}, getting next scan date for main schedule")
    pattern = re.compile(re.escape('_ad'), re.IGNORECASE)
    adhoc = ['adhoc', 'ad-hoc', 'ad_hoc']
    if any(x in tag.lower() for x in adhoc):
        tag = pattern.split(tag)[0]
    elif '_' in tag:
        tag = tag.split("_")[0]
    print(tag, name)
    SEARCH_ENDPOINT = 'search/was/wasscanschedule'
    req = E.ServiceRequest(
        E.preferences(
            # E.verbose("true" if VERBOSE else "false"),
            # should only be 1 active reoccuring shcedule per tag
            E.limitResults(RESULTS_LIMIT)
        ),
        E.filters(
            E.Criteria('true', field='active', operator='EQUALS'),
            E.Criteria(name, field='name', operator='CONTAINS'),
            E.Criteria(tag, field='name', operator='CONTAINS')
        ),

    )
    res_str: str = qgc.request(SEARCH_ENDPOINT, req, http_method="post")
    res_xml: ObjectifiedElement = fromstring(res_str.encode())
    return res_xml.data.WasScanSchedule.nextLaunchDate.text
