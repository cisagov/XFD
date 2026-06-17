"""File for managing parameters and authentication."""

# Standard Python Libraries
from configparser import ConfigParser
import os

# Central .ini file
curr_dir = os.path.dirname(os.path.abspath(__file__))
ini_path = os.path.join(curr_dir, "..", "pe_reports", "parameters.ini")
INI_FILE = os.path.normpath(ini_path)


def get_params(section):
    """Retrieve parameters from the specified section of the central ini file."""
    # Verify .ini file found
    if os.path.isfile(INI_FILE):
        parser = ConfigParser()
        parser.read(INI_FILE, encoding="utf-8")
        # Verify specified section exists in .ini file
        if parser.has_section(section):
            params = dict(parser.items(section))
        else:
            raise Exception(
                'Section "{}" not found in the "{}" file'.format(section, INI_FILE)
            )
    else:
        raise Exception('File not found at this path: "{}"'.format(INI_FILE))
    return params
