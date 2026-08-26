class Stakeholder:
    """
    A class used to represent a WAS stakeholder
    ...
    Attributes
    ----------
    name : str
        organization name
    tag_id : int
        qualys tag id number
    next_scan_date : str
        string representation of next scan date ex: 7/26/24
    launched_date : str
        string representation of the most recent scan launch date ex: 7/26/24
    schedule_id : int
        the qualys schedule id number
    """

    def __init__(self, name, tag_id, next_scan_date, launched_date, schedule_id, cadence):
        self.name: str = name
        self.tag_id: int = tag_id
        self.next_scan_date: str = next_scan_date
        self.launched_date: str = launched_date
        self.schedule_id: int = schedule_id
        self.cadence: str = cadence
