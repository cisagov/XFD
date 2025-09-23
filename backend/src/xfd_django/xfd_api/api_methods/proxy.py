"""API methods to support Proxy endpoints."""

# Standard Python Libraries
from typing import Optional

# Third-Party Libraries
from fastapi import Request
from fastapi.responses import Response
import httpx


# Helper function to handle cookie manipulation
def manipulate_cookie(request: Request, cookie_name: str):
    """Manipulate cookie."""
    cookies = request.cookies.get(cookie_name)
    if cookies:
        return {cookie_name: cookies}
    return {}


# Helper function to proxy requests
async def proxy_request(
    request: Request,
    target_url: str,
    path: Optional[str] = None,
    cookie_name: Optional[str] = None,
):
    """Proxy the request to the target URL."""
    headers = dict(request.headers)

    # Cookie manipulation for specific cookie names
    if cookie_name:
        cookies = manipulate_cookie(request, cookie_name)
        if cookies:
            headers["Cookie"] = "{}={}".format(cookie_name, cookies[cookie_name])

    client = getattr(request.app.state, "httpx", None)
    _temp_client = None
    if client is None:  # fallback for tests/CLI without startup
        _temp_client = httpx.AsyncClient(timeout=httpx.Timeout(20.0))
        client = _temp_client

    try:
        proxy_response = await client.request(
            method=request.method,
            url="{}/{}".format(target_url, path),
            headers=headers,
            params=request.query_params,
            content=await request.body(),
        )
    finally:
        if _temp_client is not None:
            await _temp_client.aclose()

    # Remove chunked encoding for API Gateway compatibility
    proxy_response_headers = dict(proxy_response.headers)
    proxy_response_headers.pop("transfer-encoding", None)

    return Response(
        content=proxy_response.content,
        status_code=proxy_response.status_code,
        headers=proxy_response_headers,
    )
