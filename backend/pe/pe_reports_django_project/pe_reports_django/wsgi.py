"""WSGI config for pe_reports_django project."""

# Standard Python Libraries
import os

# Third-Party Libraries
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pe_reports_django.settings")

application = get_wsgi_application()
