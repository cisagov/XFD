from starlette.responses import Response, StreamingResponse, RedirectResponse
from fastapi import Request, status
from xfd_api.api_methods import proxy
import logging

LOGGER = logging.getLogger(__name__)

def sanitize_and_stream_response(proxy_response: Response) -> StreamingResponse:
    """Wraps a proxy response in StreamingResponse and strips conflicting headers."""
    # Filter headers that can cause issues when manually constructing a response
    safe_headers = {
        key: value for key, value in proxy_response.headers.items()
        if key.lower() not in {"content-length", "transfer-encoding", "content-encoding"}
    }

    return StreamingResponse(
        iter([proxy_response.body]),
        status_code=proxy_response.status_code,
        headers=safe_headers
    )


async def matomo_proxy_request(
    request: Request,
    MATOMO_URL: str,
    path: str
):
    """Proxy requests to the Matomo analytics instance."""
    
    # Public paths -- directly allowed
    allowed_paths = ["/matomo.php", "/matomo.js"]
    if any(
        [request.url.path.startswith(allowed_path) for allowed_path in allowed_paths]
    ):
        return await proxy.proxy_request(path, request, MATOMO_URL)

    # Redirects for specific font files
    if request.url.path in [
        "/plugins/Morpheus/fonts/matomo.woff2",
        "/plugins/Morpheus/fonts/matomo.woff",
        "/plugins/Morpheus/fonts/matomo.ttf",
    ]:
        return RedirectResponse(
            url="https://cdn.jsdelivr.net/gh/matomo-org/matomo@5.2.1{}".format(
                request.url.path
            )
        )
    try:
        # Handle the proxy request to Matomo
        proxy_response = await proxy.proxy_request(path=path, request=request, target_url=MATOMO_URL)
        return sanitize_and_stream_response(proxy_response)
    except Exception as e:
        LOGGER.error("Error while proxying request to Matomo: %s", e)
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)