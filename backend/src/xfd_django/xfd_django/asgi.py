"""
ASGI config for xfd_django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

# Standard Python Libraries
import asyncio
from asyncio import Semaphore
import logging
import os
import threading

# Third-Party Libraries
import django
from django.apps import apps
from django.conf import settings
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from mangum import Mangum
from redis import asyncio as aioredis
from xfd_api.tasks.scheduler import handler as scheduler_handler
from xfd_django.docker_events import listen_for_docker_events
from xfd_django.middleware.middleware import LoggingMiddleware

LOGGER = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Ensure apps are populated
apps.populate(settings.INSTALLED_APPS)


def set_security_headers(response: Response, isMatomo):
    """Apply security headers to the HTTP response."""
    # Conditionally set Content Security Policy (CSP) based on the request URL

    # TODO: Uncomment the following lines if you want to set CSP for Matomo
    if isMatomo:
        csp_value = "; ".join(
            [
                "{} {}".format(key, " ".join(map(str, value)))
                for key, value in settings.MATOMO_CONTENT_SECURITY_POLICY.items()
                if isinstance(value, (list, tuple))
            ]
        )
        response.headers["Content-Security-Policy"] = csp_value
    else:
        # Set Secure Content Security Policy (CSP)
        csp_value = "; ".join(
            [
                "{} {}".format(key, " ".join(map(str, value)))
                for key, value in settings.SECURE_CSP_POLICY.items()
                if isinstance(value, (list, tuple))
            ]
        )
        response.headers["Content-Security-Policy"] = csp_value

    # Set Strict-Transport-Security (HSTS)
    hsts_value = "max-age={}".format(settings.SECURE_HSTS_SECONDS)
    if settings.SECURE_HSTS_PRELOAD:
        hsts_value += "; preload"
    if settings.SECURE_HSTS_INCLUDE_SUBDOMAINS:
        hsts_value += "; includeSubDomains"
    response.headers["Strict-Transport-Security"] = hsts_value

    # Additional security headers
    response.headers["X-XSS-Protection"] = (
        "1; mode=block" if settings.SECURE_BROWSER_XSS_FILTER else "0"
    )
    response.headers["X-Content-Type-Options"] = (
        "nosniff" if settings.SECURE_CONTENT_TYPE_NOSNIFF else ""
    )
    response.headers["Cache-Control"] = settings.SECURE_CACHE_CONTROL
    response.headers["Access-Control-Allow-Credentials"] = (
        "true" if settings.SECURE_ACCESS_CONTROL_ALLOW_CREDENTIALS else "false"
    )

    return response


def get_application() -> FastAPI:
    """Get application."""
    # Import views after Django setup
    # Third-Party Libraries
    from xfd_api.views import api_router  # pylint: disable=C0415

    app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)

    # Create one pooled client on startup
    @app.on_event("startup")
    async def _httpx_startup():
        app.state.httpx = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5, read=30, write=30, pool=30),
            limits=httpx.Limits(
                max_connections=200,
                max_keepalive_connections=50,
                keepalive_expiry=60.0,
            ),
            http2=False,
        )

    # Close it on shutdown
    @app.on_event("shutdown")
    async def _httpx_shutdown():
        await app.state.httpx.aclose()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add security headers middleware
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        isMatomo = bool(request.url.path.startswith("/matomo"))
        return set_security_headers(response, isMatomo)

    app.add_middleware(LoggingMiddleware)

    app.include_router(api_router)

    # ── Generic exception handler ────────────────────────────────
    @app.exception_handler(Exception)
    async def _handle_uncaught_exceptions(request: Request, exc: Exception):
        # TODO: log exc via your logger here, e.g. logger.exception(exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_errors(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    @app.on_event("startup")
    async def startup():
        """Start up Redis with ElastiCache."""
        # Initialize Redis with the ElastiCache endpoint
        app.state.redis = await aioredis.from_url(
            "redis://{}".format(settings.ELASTICACHE_ENDPOINT),
            encoding="utf-8",
            decode_responses=True,
            max_connections=100,
            socket_timeout=5,
        )
        app.state.redis_semaphore = Semaphore(20)

        # Run scheduler during local development. When deployed on AWS,
        # the scheduler runs on a separate lambda function.
        if settings.IS_LOCAL:
            # Start listening for Docker events
            run_docker_events_listener()

            # Start the scheduler in local development
            asyncio.create_task(run_scheduler())

    @app.on_event("shutdown")
    async def redis_shutdown():
        """Shut down Redis connection."""
        await app.state.redis.close()
        await app.state.redis.connection_pool.disconnect()

    return app


def run_docker_events_listener():
    """Run the Docker events listener for local development in a separate thread."""
    thread = threading.Thread(target=listen_for_docker_events, daemon=True)
    thread.start()
    LOGGER.info("Docker events listener started in a separate thread.")


async def run_scheduler():
    """Run the scheduler in local development."""
    try:
        LOGGER.info("Starting local scheduler...")
        while True:
            await scheduler_handler({}, {})
            await asyncio.sleep(120)  # Run every 120 seconds
    except Exception as e:
        LOGGER.error("Error running local scheduler: %s", e)


app = get_application()
handler = Mangum(app)
