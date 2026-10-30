"""Views for the core application."""

# Third-Party Libraries
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Render the initial WAS Reporting application landing page."""
    return render(request, "core/home.html", {"page_title": "WAS Reporting"})


def health(request: HttpRequest) -> JsonResponse:
    """Return a minimal response for local and AWS health checks."""
    return JsonResponse({"status": "ok"})
