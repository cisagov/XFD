"""API methods to proxy Matomo requests."""
# Standard Python Libraries
import logging
import os
from typing import Dict, List, Tuple
from urllib.parse import urlparse, urlunparse

# Third-Party Libraries
from fastapi import Request
from starlette.datastructures import MutableHeaders
from starlette.responses import RedirectResponse, Response, StreamingResponse
from starlette.types import Scope
from xfd_api.api_methods import proxy

LOGGER = logging.getLogger(__name__)

PUBLIC_PREFIX = "/matomo"
PUBLIC_COLLECTORS = {"matomo.php", "matomo.js"}
CDN_FONT_PATHS = {
    "plugins/Morpheus/fonts/matomo.woff2",
    "plugins/Morpheus/fonts/matomo.woff",
    "plugins/Morpheus/fonts/matomo.ttf",
}
STRIP_RESPONSE_HEADERS = {
    "content-length",
    "transfer-encoding",
    "content-encoding",
    "connection",
    "strict-transport-security",
}
DEBUG = os.getenv("MATOMO_PROXY_DEBUG", "").lower() in ("1", "true", "yes")


def _join_public(public_prefix: str, suffix: str) -> str:
    return "{}/{}".format(public_prefix.rstrip("/"), suffix.lstrip("/"))


def _pick_public_host_and_proto(request: Request) -> tuple[str, str]:
    hdr = request.headers
    xfh = hdr.get("x-forwarded-host")
    if xfh:
        public_host = xfh.split(",", 1)[0].strip()
        proto = (
            (hdr.get("x-forwarded-proto") or request.url.scheme)
            .split(",", 1)[0]
            .strip()
        )
        return public_host, proto

    origin = hdr.get("origin")
    if origin:
        u = urlparse(origin)
        if u.netloc:
            return (u.netloc, u.scheme or request.url.scheme)

    ref = hdr.get("referer")
    if ref:
        u = urlparse(ref)
        if u.netloc:
            return (u.netloc, u.scheme or request.url.scheme)

    return (hdr.get("host", ""), request.url.scheme)


def _build_forward_headers(request: Request, public_prefix: str) -> Dict[str, str]:
    public_host, public_proto = _pick_public_host_and_proto(request)
    client_ip = getattr(request.client, "host", "")
    prior_xff = request.headers.get("x-forwarded-for")
    # cache URL parts once
    url = request.url
    path = url.path
    query = url.query

    # Build headers dict in one go to minimize rehashing
    hdrs: Dict[str, str] = {
        "forwarded": "for={};proto={};host={}".format(
            client_ip, public_proto, public_host
        ),
        "x-forwarded-for": (
            "{}, {}".format(prior_xff, client_ip) if prior_xff else client_ip
        ),
        "x-forwarded-host": public_host,
        "x-forwarded-proto": public_proto,
        "x-forwarded-prefix": public_prefix,
        # Passing prefix only avoids redirect loop (preserve current behavior)
        "x-forwarded-uri": public_prefix,
        # Track full original path+query for diagnostics (preserve current behavior)
        "x-original-uri": "{}?{}".format(path, query) if query else path,
    }
    return hdrs


def _rewrite_location_header(
    headers: MutableHeaders,
    *,
    target_base: str,
    public_prefix: str,
    public_host: str,
    public_proto: str,
) -> None:
    loc = headers.get("location")
    if not loc:
        return

    loc = loc.strip()
    if not loc:
        headers["location"] = _join_public(public_prefix, "/")
        return

    # helper to turn ".../index.php" (no query) into ".../"
    def _dir_if_index_no_query(path: str, query: str) -> str:
        if (
            path.endswith("/index.php") or path == "/index.php" or path == "index.php"
        ) and not query:
            if path.endswith("/index.php"):
                return path[: -len("/index.php")] + "/"
            # "index.php" alone → "/matomo/"
            return _join_public(public_prefix, "/")
        return path

    # 1) Absolute internal
    if loc.startswith(target_base):
        suffix = loc[len(target_base) :]
        qpos = suffix.find("?")
        path_only = suffix if qpos == -1 else suffix[:qpos]
        query_only = "" if qpos == -1 else suffix[qpos + 1 :]
        path_only = _dir_if_index_no_query(path_only, query_only)
        new_suffix = path_only + ("" if not query_only else "?" + query_only)
        headers["location"] = _join_public(public_prefix, new_suffix or "/")
        return

    parsed = urlparse(loc)

    # 2) Absolute public
    if parsed.scheme and parsed.netloc:
        if parsed.netloc == public_host:
            path = parsed.path or "/"
            if not path.startswith(public_prefix):
                path = _join_public(public_prefix, path if path != "/" else "/")
            path = _dir_if_index_no_query(path, parsed.query)
            new = parsed._replace(scheme=public_proto, netloc=public_host, path=path)
            headers["location"] = urlunparse(new)
            return
        return

    # 3) Root-relative
    if loc.startswith("/"):
        # keep "/" as directory
        path = loc if loc != "/" else _join_public(public_prefix, "/")
        qpos = path.find("?")
        path_only = path if qpos == -1 else path[:qpos]
        query_only = "" if qpos == -1 else path[qpos + 1 :]
        path_only = _dir_if_index_no_query(path_only, query_only)
        new_loc = (
            _join_public(public_prefix, path_only)
            if not path_only.startswith(public_prefix)
            else path_only
        )
        if query_only:
            new_loc = new_loc + "?" + query_only
        headers["location"] = new_loc
        return

    # 4) Query-only or "./" → index.php (these *do* need index.php)
    if loc.startswith("?") or loc in (".", "./"):
        q = loc[1:] if loc.startswith("?") else ""
        headers["location"] = _join_public(
            public_prefix, "/index.php" + ("" if not q else "?" + q)
        )
        return

    # 5) "./index.php..." → normalize relative
    if loc.startswith("./"):
        loc = loc[2:]

    # 6) Other relative
    qpos = loc.find("?")
    rel_path = loc if qpos == -1 else loc[:qpos]
    rel_query = "" if qpos == -1 else loc[qpos + 1 :]
    rel_path = _dir_if_index_no_query(rel_path, rel_query)
    new_rel = _join_public(public_prefix, "/" + rel_path)
    headers["location"] = new_rel + ("?" + rel_query if rel_query else "")


def _clone_request_with_headers(request: Request, extra: Dict[str, str]) -> Request:
    scope: Scope = dict(request.scope)
    # avoid recreating sets per-iteration
    drop_keys = {"host", "content-length", "connection"} | set(extra.keys())
    filtered: List[Tuple[bytes, bytes]] = [
        (k, v)
        for (k, v) in list(scope.get("headers", []))
        if k.decode("latin-1").lower() not in drop_keys
    ]
    # append extras (encode once)
    filtered.extend(
        (name.encode("latin-1"), str(value).encode("latin-1"))
        for name, value in extra.items()
    )
    scope["headers"] = filtered
    return Request(scope, receive=request.receive)


def _stream_back_with_rewrites(
    upstream_resp: Response,
    *,
    target_base: str,
    public_prefix: str,
    public_host: str,
    public_proto: str,
) -> StreamingResponse:
    # Filter headers in one pass
    safe_headers = {
        k: v
        for k, v in upstream_resp.headers.items()
        if k.lower() not in STRIP_RESPONSE_HEADERS
    }

    _rewrite_location_header(
        MutableHeaders(safe_headers),
        target_base=target_base.rstrip("/"),
        public_prefix=public_prefix,
        public_host=public_host,
        public_proto=public_proto,
    )

    # StreamingResponse can take a tuple/iterable; keep identical behavior
    resp = StreamingResponse(
        (upstream_resp.body,),
        status_code=upstream_resp.status_code,
        headers=safe_headers,
    )
    return resp


async def _call_proxy_with_headers(
    *, path: str, request: Request, target_base: str, fwd_headers: Dict[str, str]
) -> Response:
    cloned_req = _clone_request_with_headers(request, fwd_headers)
    return await proxy.proxy_request(
        request=cloned_req, target_url=target_base, path=path
    )


async def matomo_proxy_request(request: Request, MATOMO_URL: str, path: str):
    """Proxy Matomo requests, rewriting paths and headers as needed."""
    target_base = (MATOMO_URL or "").strip().rstrip("/")
    if not target_base.startswith(("http://", "https://")):
        msg = "VITE_MATOMO_URL must include http(s) scheme, e.g. http://matomo:80"
        LOGGER.error("%s (got: %r)", msg, MATOMO_URL)
        return Response(status_code=500, content=msg.encode())

    clean_path = path.lstrip("/")

    # public collectors
    if clean_path in PUBLIC_COLLECTORS:
        try:
            upstream = await proxy.proxy_request(
                path=clean_path, request=request, target_url=target_base
            )
            LOGGER.debug(
                "Upstream Set-Cookie(s): %r",
                getattr(
                    upstream.headers, "getlist", lambda k: [upstream.headers.get(k)]
                )("set-cookie"),
            )
            public_host, public_proto = _pick_public_host_and_proto(request)
            return _stream_back_with_rewrites(
                upstream,
                target_base=target_base,
                public_prefix=PUBLIC_PREFIX,
                public_host=public_host,
                public_proto=public_proto,
            )
        except Exception as e:
            LOGGER.exception("Matomo collector proxy error: %s", e)
            return Response(
                status_code=502,
                content=(
                    "Collector error: {!r}".format(e).encode()
                    if DEBUG
                    else b"Bad Gateway"
                ),
            )

    # CDN font redirects
    if clean_path in CDN_FONT_PATHS:
        return RedirectResponse(
            url="https://cdn.jsdelivr.net/gh/matomo-org/matomo@5.2.1/{}".format(
                clean_path
            ),
            status_code=302,
        )

    # normal proxied requests
    fwd_headers = _build_forward_headers(request, PUBLIC_PREFIX)
    public_host = fwd_headers["x-forwarded-host"]
    public_proto = fwd_headers["x-forwarded-proto"]

    # Guard 2: if the browser hit /matomo/index.php (no query), upstream must see "/"
    proxied_path = clean_path
    if proxied_path in ("", "/"):
        proxied_path = "/"
    elif proxied_path.lower() == "index.php" and not request.url.query:
        proxied_path = "/"

    try:
        upstream = await _call_proxy_with_headers(
            path=proxied_path,
            request=request,
            target_base=target_base,
            fwd_headers=fwd_headers,
        )
        LOGGER.debug(
            "Upstream Set-Cookie(s): %r",
            getattr(upstream.headers, "getlist", lambda k: [upstream.headers.get(k)])(
                "set-cookie"
            ),
        )
    except Exception as e:
        LOGGER.exception("Error while proxying request to Matomo: %s", e)
        return Response(
            status_code=502,
            content=(
                "Upstream error: {!r}".format(e).encode() if DEBUG else b"Bad Gateway"
            ),
        )

    return _stream_back_with_rewrites(
        upstream,
        target_base=target_base,
        public_prefix=PUBLIC_PREFIX,
        public_host=public_host,
        public_proto=public_proto,
    )
