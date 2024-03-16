"""
This module contains tests for the SignRequests class in the mitmproxy_sign_requests module.

It includes tests for different scenarios such as when a user agent and signature are set, and when they are not set.
"""

# Standard Python Libraries
import os

# Third-Party Libraries
from dotenv import load_dotenv
from mitmproxy.test import taddons, tflow

from .mitmproxy_sign_requests import SignRequests

load_dotenv()


def test_user_agent_and_signature():
    """
    This function tests the SignRequests class with a user agent and signature set.

    It creates an instance of the SignRequests class with a user agent and signature, makes a request, and verifies the
    signature.
    """
    sr = SignRequests(
        key_id="crossfeed",
        public_key=os.getenv("WORKER_SIGNATURE_PUBLIC_KEY"),
        private_key=os.getenv("WORKER_SIGNATURE_PRIVATE_KEY"),
        user_agent="custom user agent",
    )
    with taddons.context():
        f = tflow.tflow()
        f.request.headers["User-Agent"] = "original user agent"
        sr.request(f)
        assert f.request.headers["User-Agent"] == "custom user agent"
        sr.verify_signature(
            method=f.request.method,
            url=f.request.url,
            date=f.request.headers["Date"],
            signature=f.request.headers["Signature"],
        )


def test_no_user_agent_or_signature_set():
    """
    This function tests the SignRequests class without a user agent and signature set.

    It creates an instance of the SignRequests class without a user agent and signature, makes a request, and checks
    that no user agent, date, or signature headers are set.
    """
    sr = SignRequests(key_id="", public_key="", private_key="", user_agent="")
    with taddons.context():
        f = tflow.tflow()
        sr.request(f)
        assert "User-Agent" not in f.request.headers
        assert "Date" not in f.request.headers
        assert "Signature" not in f.request.headers
