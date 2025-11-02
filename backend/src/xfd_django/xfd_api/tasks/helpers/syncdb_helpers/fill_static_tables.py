"""Functions used to fill static/lookup tables in the mdl."""

# Standard Libraries
# Standard Python Libraries
import logging

# Third-Party Libraries
from django.db import IntegrityError
from xfd_mini_dl.models import NMIServiceGroup, RiskyServiceGroup

LOGGER = logging.getLogger(__name__)

risky_service_map = {
    "ms-wbt-server": "rdp",
    "telnet": "telnet",
    "rtelnet": "telnet",
    "microsoft-ds": "smb",
    "smbdirect": "smb",
    "ldap": "ldap",
    "netbios-ns": "netbios",
    "netbios-dgm": "netbios",
    "netbios-ssn": "netbios",
    "ftp": "ftp",
    "rsftp": "ftp",
    "ni-ftp": "ftp",
    "tftp": "ftp",
    "bftp": "ftp",
    "msrpc": "rpc",
    "sqlnet": "sql",
    "sqlserv": "sql",
    "sql-net": "sql",
    "sqlsrv": "sql",
    "msql": "sql",
    "mini-sql": "sql",
    "mysql-cluster": "sql",
    "ms-sql-s": "sql",
    "ms-sql-m": "sql",
    "irc": "irc",
    "kerberos-sec": "kerberos",
    "kpasswd5": "kerberos",
    "klogin": "kerberos",
    "kshell": "kerberos",
    "kerberos-adm": "kerberos",
    "kerberos": "kerberos",
    "kerberos_master": "kerberos",
    "krb_prop": "kerberos",
    "krbupdate": "kerberos",
    "kpasswd": "kerberos",
}

nmi_service_group_map = {
    "microsoft-ds": "smb",
    "ms-wbt-server": "rdp",
    "rtelnet": "telnet",
    "smbdirect": "smb",
    "telnet": "telnet",
}


def fill_risky_service_lookup_table():
    """Fill the RiskyServiceGroup lookup table with static data."""
    for service_name, group in risky_service_map.items():
        try:
            RiskyServiceGroup.objects.update_or_create(
                service_name=service_name, defaults={"group": group}
            )
        except IntegrityError as e:
            LOGGER.error("Error adding %s: %s", service_name, e)


def fill_nmi_service_group_table():
    """Fill the NMIServiceGroup lookup table with static data."""
    for service_name, group in nmi_service_group_map.items():
        try:
            NMIServiceGroup.objects.update_or_create(
                service_name=service_name, defaults={"group": group}
            )
        except IntegrityError as e:
            LOGGER.error("Error adding %s: %s", service_name, e)
