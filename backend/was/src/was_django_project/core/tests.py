"""Smoke tests for the WAS Django application foundation."""

# Standard Python Libraries
import logging
from unittest.mock import patch

# Third-Party Libraries
from django.conf import settings
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


class DjangoLoggingConfigurationTests(SimpleTestCase):
    """Verify portable console logging for every planned WAS runtime."""

    def test_django_manages_logging_configuration(self) -> None:
        """Apply logging after settings load through Django's configurator."""
        self.assertEqual(settings.LOGGING_CONFIG, "logging.config.dictConfig")

    def test_logging_uses_only_console_handlers(self) -> None:
        """Route local, Lambda, and Fargate records to process output."""
        logging_settings = settings.LOGGING

        self.assertEqual(set(logging_settings["handlers"]), {"console"})
        self.assertEqual(
            logging_settings["handlers"]["console"]["class"],
            "logging.StreamHandler",
        )
        self.assertEqual(logging_settings["root"]["handlers"], ["console"])
        self.assertEqual(
            logging_settings["loggers"]["django"]["handlers"],
            ["console"],
        )
        for logger_name in settings.WAS_LOGGER_NAMES:
            self.assertEqual(
                logging_settings["loggers"][logger_name]["handlers"],
                ["console"],
            )

    def test_owned_loggers_and_handler_use_configured_log_level(self) -> None:
        """Apply the selected level only to WAS-owned logger namespaces."""
        self.assertEqual(settings.LOGGING["root"]["level"], "INFO")
        self.assertEqual(
            settings.LOGGING["handlers"]["console"]["level"],
            settings.LOGGING_LEVEL,
        )
        for logger_name in settings.WAS_LOGGER_NAMES:
            self.assertEqual(
                settings.LOGGING["loggers"][logger_name]["level"],
                settings.LOGGING_LEVEL,
            )

    def test_owned_logger_names_emit_once(self) -> None:
        """Route Django, UI, reporting, and mailer records without duplication."""
        root_handler = logging.getLogger().handlers[0]
        django_handler = logging.getLogger("django").handlers[0]
        self.assertIs(root_handler, django_handler)

        logger_names = (
            "core.views",
            "was_reports.qualys.qualys_client",
            "was_mailer.email_reports",
            "django.request",
        )
        for logger_name in logger_names:
            with self.subTest(logger=logger_name), patch.object(
                root_handler, "emit"
            ) as emit_record:
                logging.getLogger(logger_name).info("logging route test")

                emit_record.assert_called_once()

    def test_unrelated_sdk_debug_record_is_suppressed(self) -> None:
        """Keep third-party request metadata out of local debug output."""
        root_handler = logging.getLogger().handlers[0]

        with patch.object(root_handler, "emit") as emit_record:
            logging.getLogger("botocore.endpoint").debug("sensitive request details")

            emit_record.assert_not_called()
