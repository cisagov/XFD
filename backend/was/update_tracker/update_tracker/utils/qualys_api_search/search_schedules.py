import sys
from datetime import timedelta

from lxml.builder import E
from lxml.objectify import ObjectifiedElement, fromstring
from models.stakeholder import Stakeholder
from set_up import log_exception, qgc
from was_reports.data.daily_report_tracker import (
    latest_tracker_pull_date,
    recent_schedule_ids,
)
from was_reports.utils.database import close, connect
from utils.qualys_api_search.search_utils import (make_stakeholder_info,
                                                  nextdate_for_adhoc)

VERBOSE = True
RESULTS_LIMIT = 50

# get the most recent date in the tracker minus 48 hours
# scan time limit 24 hrs, go back extra time to ensure all scans are picked up
conn = connect()
try:
    INPUT_DATE_DT = latest_tracker_pull_date(conn) - timedelta(hours=48)
    PREVIOUS_IDS = recent_schedule_ids(conn, INPUT_DATE_DT)
finally:
    close(conn)

INPUT_DATE = INPUT_DATE_DT.strftime(
    '%Y-%m-%dT%H:%M:%SZ')  # qualys api datetime format
# INPUT_DATE = INPUT_DATE_DT.strftime('%Y-%m-%d')


def get_tag_id(tag_name: str) -> int:
    endpoint = 'search/am/tag'
    method = 'post'
    req = E.ServiceRequest(
        E.filters(
            E.Criteria(tag_name, field='name', operator='EQUALS')
        )
    )
    res_str: str = qgc.request(endpoint, req, http_method=method)
    res_xml: ObjectifiedElement = fromstring(res_str.encode())
    try:
        return int(res_xml.data.Tag.id.text)
    except (AttributeError, ValueError):
        raise ValueError("Tag ID not found for tag name: {}".format(tag_name))


def search_schedules(stakeholder_tag=None):
    """
    Searches the qualys api for schedules finished after the input date

    Excepts
    ------
    AttributeError
        If there are no finished schedules that match the criteria
        If the schedule is inactive

    Parameters
    ----------
    stakeholder_tag : str, optional
        exact stakeholder tag to process during schedule discovery

    Returns
    -------
    stakeholders : dict
        mapping of tag to stakeholder object
    """
    SEARCH_ENDPOINT = 'search/was/wasscanschedule'
    offset: int = 1  # Qualys API indexes offset at 1
    offset_element = E.startFromOffset(str(offset))
    req = E.ServiceRequest(
        E.preferences(
            # E.verbose("true" if VERBOSE else "false"),
            E.limitResults(str(RESULTS_LIMIT)),
            offset_element,
        ),
        E.filters(
            E.Criteria(INPUT_DATE.split('T')[0], field='lastScan.launchedDate',
                       operator='GREATER'),
            # E.Criteria('FINISHED, ERROR',
            #            field='lastScan.status', operator='IN'),
            E.Criteria('RUNNING', field='lastScan.status', operator='NOT EQUALS'),
            # E.Criteria('FINISHED', field='lastScan.status', operator='IN'),
            # E.Criteria('ERROR', field='lastScan.status', operator='IN'),
            E.Criteria('VULNERABILITY', field='type', operator='EQUALS')
        )
    )
    # print(etree.tostring(req, pretty_print=True).decode("utf-8"))
    # xml_bytes = etree.tostring(
    # req,
    # pretty_print=True,
    # xml_declaration=True,
    # encoding="UTF-8"
    # )
    # print(xml_bytes)
    print("Last Tracker Day: {}".format(INPUT_DATE))
    print("getting finished schedules from qualys...")
    stakeholders = {}  # dictionary to map tags to stakeholder objects
    has_more: bool = True
    while has_more:
        # while count >= RESULTS_LIMIT:
        print("Fetching offset {}...".format(offset))

        res_str: str = qgc.request(
            SEARCH_ENDPOINT, req, http_method="post")
        res_xml: ObjectifiedElement = fromstring(res_str.encode())
        offset += res_xml.count
        offset_element.text = str(offset)
        try:
            has_more = res_xml.hasMoreRecords
        except AttributeError as e:
            log_exception(exc=e, min_launch_date=INPUT_DATE)
            sys.exit("ERROR: No schedules found. Review dailywas.log for query")
        # count = res_xml.count
        for schedule in res_xml.data.WasScanSchedule:
            # print(etree.tostring(schedule, pretty_print=True).decode("utf-8"))
            schedule_id = int(schedule.id.text)
            if schedule_id not in PREVIOUS_IDS:
                tag, name = make_stakeholder_info(schedule.name.text)
                if stakeholder_tag is not None and tag != stakeholder_tag:
                    continue
                # tag_id: int = schedule.target.tags.included.tagList.list.Tag.id
                tag_id: int = get_tag_id(tag)
                # launched_date: str = schedule.lastScan.launchedDate.text
                cadence = schedule.scheduling.occurrenceType.text
                try:
                    next_scan_date: str = schedule.nextLaunchDate.text
                except AttributeError:
                    next_scan_date: str = nextdate_for_adhoc(tag, name)
                if tag not in stakeholders:
                    # stakeholders[tag] = Stakeholder(name, tag_id, next_scan_date, launched_date, schedule_id, cadence)
                    stakeholders[tag] = Stakeholder(
                        name,
                        tag_id,
                        next_scan_date,
                        INPUT_DATE,
                        schedule_id,
                        cadence,
                    )

            else:
                print("Skipping duplicate: {}".format(schedule.name.text))
    print("Schedules found successfully")
    print("There are {} reports today".format(len(stakeholders)))
    return stakeholders
