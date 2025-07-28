"""Utility functions for hashing.

Provides functions for generating SHA-256 hashes.
"""

# Standard Python Libraries
import hashlib


def hash_ip(ip_address: str) -> str:
    """Generate a SHA-256 hash of the given IP address.

    Args:
        ip_address (str): The IP address to hash.

    Returns:
        str: The SHA-256 hash of the IP address.
    """
    return hashlib.sha256(ip_address.encode()).hexdigest()
