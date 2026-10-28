"""
ASGI config for was_django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

# Standard Python Libraries
import os

# Third-Party Libraries
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "was_django.settings")

application = get_asgi_application()
