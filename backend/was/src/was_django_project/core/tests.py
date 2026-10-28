"""Smoke tests for the WAS Django application foundation."""

# Third-Party Libraries
from django.contrib.messages import constants as message_constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import resolve, reverse
from mangum import Mangum

# Local Application
from was_django.asgi import application, handler


class DjangoFoundationSmokeTests(SimpleTestCase):
    """Verify the initial pages and serverless application entry point."""

    def test_landing_page_response(self) -> None:
        """Return the landing page through the named root route."""
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "WAS Reporting")

    def test_health_endpoint_response(self) -> None:
        """Return only the expected status from the health endpoint."""
        response = self.client.get(reverse("core:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_base_template_renders_shared_landmarks(self) -> None:
        """Render the shared shell with its skip link and main landmark."""
        rendered_template = render_to_string(
            "core/home.html",
            {
                "DEFAULT_MESSAGE_LEVELS": message_constants.DEFAULT_LEVELS,
                "messages": [Message(message_constants.ERROR, "Example error message")],
                "page_title": "Foundation smoke test",
            },
        )

        self.assertIn("<title>", rendered_template)
        self.assertIn("Foundation smoke test", rendered_template)
        self.assertIn("css/was.css", rendered_template)
        self.assertIn('href="#main-content"', rendered_template)
        self.assertIn('id="main-content"', rendered_template)
        self.assertIn('aria-label="Primary navigation"', rendered_template)
        self.assertIn("Error:", rendered_template)
        self.assertIn("Example error message", rendered_template)

    def test_mangum_handler_wraps_asgi_application(self) -> None:
        """Expose the Django ASGI application through Mangum for Lambda."""
        self.assertIsInstance(handler, Mangum)
        self.assertIs(handler.app, application)

    def test_root_url_resolves_to_named_home_view(self) -> None:
        """Load the project URL configuration and resolve its root route."""
        resolved_url = resolve("/")

        self.assertEqual(resolved_url.view_name, "core:home")
