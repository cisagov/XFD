"""Collect Shodan data."""

# Standard Python Libraries
# from datetime import timedelta
import logging
import threading

# Third-Party Libraries
import numpy
from pe_source.data.config_source import shodan_api_init
from pe_source.data.db_query_source import get_orgs
from pe_source.shodan.shodan_helpers import run_shodan_thread

# Logging
LOGGER = logging.getLogger(__name__)


class Get_shodan:
    """Fetch Shodan data."""

    def __init__(self, orgs_list):
        """Initialize Shodan class."""
        self.orgs_list = orgs_list

    def run_shodan(self):
        """Run Shodan calls."""
        orgs_list = self.orgs_list

        # Retrieve full org info from PE database
        pe_orgs = get_orgs()
        pe_orgs_final = []
        if orgs_list == "all":
            for pe_org in pe_orgs:
                if pe_org["report_on"]:
                    pe_orgs_final.append(pe_org)
                else:
                    continue
        elif orgs_list == "DEMO":
            for pe_org in pe_orgs:
                if pe_org["demo"]:
                    pe_orgs_final.append(pe_org)
                else:
                    continue
        else:
            if isinstance(orgs_list, str):
                requested = {
                    part.strip() for part in orgs_list.split(",") if part.strip()
                }
            else:
                requested = set(orgs_list)
            for pe_org in pe_orgs:
                if pe_org["cyhy_db_name"] in requested:
                    pe_orgs_final.append(pe_org)
        # alphabetize orgs for consistent order
        pe_orgs_final = sorted(pe_orgs_final, key=lambda d: d["cyhy_db_name"])

        # Get list of initialized API objects
        api_list = shodan_api_init()

        # Split orgs into chunks. # of chunks = # of valid API keys = # of threads
        chunk_size = len(api_list)
        chunked_orgs_list = numpy.array_split(numpy.array(pe_orgs_final), chunk_size)

        # Start each thread
        i = 0
        thread_list = []
        while i < len(chunked_orgs_list):
            thread_name = f"Thread {i + 1}:"
            # Start thread
            t = threading.Thread(
                target=run_shodan_thread,
                args=(api_list[i], chunked_orgs_list[i], thread_name),
            )
            t.start()
            thread_list.append(t)
            i += 1

        # Wait until all threads finish to continue
        for thread in thread_list:
            thread.join()
