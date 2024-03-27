"""mitmproxy addon that signs requests and adds a Crossfeed-specific user agent."""
# Standard Python Libraries
import os
import traceback

# Third-Party Libraries
from dotenv import load_dotenv
from mitmproxy import http
import requests
from requests_http_signature import HTTPSignatureHeaderAuth

load_dotenv()


class SignRequests:
    """
    A class used to sign HTTP requests and add a Crossfeed-specific user agent.

    This class is used as a mitmproxy addon. It signs the HTTP requests using the provided private key and adds a user agent to the request headers.

    Attributes:
        key_id (str): The key ID used for signing the requests.
        private_key (str): The private key used for signing the requests.
        public_key (str): The public key used for verifying the signature.
        user_agent (str): The user agent to be added to the request headers.
        signature_auth (HTTPSignatureHeaderAuth): The HTTPSignatureHeaderAuth instance used for signing the requests.
    """

    def __init__(self, key_id="", public_key="", private_key="", user_agent=""):
        """
        Initialize the SignRequests instance.

        Args:
            key_id (str, optional): The key ID used for signing the requests. Defaults to "".
            public_key (str, optional): The public key used for verifying the signature. Defaults to "".
            private_key (str, optional): The private key used for signing the requests. Defaults to "".
            user_agent (str, optional): The user agent to be added to the request headers. Defaults to "".
        """
        self.key_id = key_id
        self.private_key = private_key
        self.public_key = public_key
        self.user_agent = user_agent
        self.signature_auth = HTTPSignatureHeaderAuth(
            key=self.private_key.encode(), key_id=key_id, algorithm="rsa-sha256"
        )

    def key_resolver(self, key_id, algorithm):
        """
        Resolve the key for the given key_id and algorithm.

        Args:
            key_id (str): The key ID used for signing the requests.
            algorithm (str): The algorithm used for signing the requests.

        Returns:
            bytes: The public key encoded in bytes.
        """
        return self.public_key.encode()

    def verify_signature(self, method, url, date, signature):
        """
        Verify the signature of the HTTP request.

        Args:
            method (str): The HTTP method of the request.
            url (str): The URL of the request.
            date (str): The date when the request was made.
            signature (str): The signature of the request.

        This method uses the HTTPSignatureHeaderAuth's verify method to verify the signature of the request.
        """
        HTTPSignatureHeaderAuth.verify(
            requests.Request(
                method=url, url=url, headers={"date": date, "Signature": signature}
            ),
            self.key_resolver,
            "Signature",
        )

    def request(self, flow):
        """
        Process the HTTP request.

        This method adds a user agent to the request headers if one is provided. If a private key is provided, it signs the request using the HTTPSignatureHeaderAuth instance.

        Args:
            flow (mitmproxy.http.HTTPFlow): The HTTP request/response flow.

        Raises:
            Exception: If there is an error while processing the request, an exception is raised and a 500 response is returned.
        """
        try:
            if self.user_agent:
                flow.request.headers["User-Agent"] = self.user_agent

            if self.private_key:
                # For ease of verification, only sign the minimum attributes required: URL, date, and method.
                signed_request = requests.Request(
                    method=flow.request.method,
                    url=flow.request.url,
                    headers={},
                    data=None,
                ).prepare()
                self.signature_auth.__call__(signed_request)
                flow.request.headers["Signature"] = signed_request.headers["Signature"]
                flow.request.headers["Date"] = signed_request.headers["Date"]

                # ctx.log.info("Sent HTTP request with signature " + signed_request.headers["Signature"])
        except Exception as e:
            flow.response = http.HTTPResponse.make(
                500,
                f"mitmproxy failed:<br> {e}<br><br>{traceback.format_exc()}",
                {"Content-Type": "text/html"},
            )


addons = [
    SignRequests(
        key_id="crossfeed",
        public_key=os.getenv("WORKER_SIGNATURE_PUBLIC_KEY", ""),
        private_key=os.getenv("WORKER_SIGNATURE_PRIVATE_KEY", ""),
        user_agent=os.getenv("WORKER_USER_AGENT", ""),
    )
]
