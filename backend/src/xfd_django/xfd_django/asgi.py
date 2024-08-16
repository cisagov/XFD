"""
ASGI config for xfd_django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""
import os
import django
from django.apps import apps
from django.conf import settings
from django.core.asgi import get_asgi_application
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
from fastapi.middleware.wsgi import WSGIMiddleware
from mangum import Mangum
from redis import asyncio as aioredis
from starlette.middleware.cors import CORSMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xfd_django.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

# Import views after Django setup
from xfd_api.views import api_router

application = get_asgi_application()

# Below this comment is custom code
apps.populate(settings.INSTALLED_APPS)

async def default_identifier(request):
    """Return default identifier."""
    return request.headers.get("X-Real-IP", request.client.host)

async def startup():
    """Start up Redis with ElastiCache."""
    # Initialize Redis with the ElastiCache endpoint using the modern Redis-Py Asyncio
    app.state.redis = await aioredis.from_url(
        f"redis://{settings.ELASTICACHE_ENDPOINT}", encoding="utf-8",
        decode_responses=True
    )


    # Initialize FastAPI Limiter with the Redis instance
    # await FastAPILimiter.init(redis, identifier=default_identifier)


def get_application() -> FastAPI:
    """get_application function."""
    app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.mount("/", WSGIMiddleware(get_asgi_application()))



    app.add_event_handler("startup", startup)

    return app

app = get_application()

handler = Mangum(app)
 