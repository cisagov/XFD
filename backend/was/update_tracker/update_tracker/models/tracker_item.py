class tracker_item:
    """
    class used to represent a row of the daily reports tracker
    ...
    Attributes
    ----------
    tag : str
        stakeholder tag
    scan_name : str
        full name of the scan excluding the slice number (WAVS - TAG - stakeholder name - Cadence Run #)
    status : str
        status of the multiscan (finished, error)
    result : str
        result of the multiscan (no web service, service error, successful, time limit reached, etc)
    launched_date : str
        string representation of the most recent scan launch date ex: 7/26/24
    next_scan_date : str
        string representation of the next scan date ex: 7/26/24
    nws : bool
        true if any or all slices of the multiscan were inaccessible (no web service)
    recent_nws: str
        html representation of inaccessible urls from the most recent scan (<br>https://url.com<br>https://webapp.com)
    removed_nws: str
        html representation of urls that were inaccessible for consecutive scans
    manual: str
        type of manual effort required to send the report, empty string if autoreport 
    schedule_id : int
        the qualys schedule id number
    """
    def __init__(self, tag, scan_name, status, result, launched_date, 
             next_scan_date, nws, recent_nws, removed_nws, manual, 
             fceb, schedule_id, qualys_errors):
        self.tag: str = tag
        self.scan_name: str = scan_name
        self.status: str = status
        self.result: str = result
        self.launched_date: str = launched_date
        self.next_scan_date: str = next_scan_date
        self.nws: bool = nws
        self.recent_nws: str = recent_nws
        self.removed_nws: str = removed_nws
        self.manual: str = manual
        self.fceb: bool = fceb
        self.schedule_id: int = schedule_id
        self.qualys_errors: str = qualys_errors