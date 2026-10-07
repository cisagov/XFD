"""DNSTwist scan source."""

# Third-Party Libraries
from pe_source.dnstwist.dnstwist import checkBlocklist, run_dnstwist

__all__ = ["checkBlocklist", "run_dnstwist"]
