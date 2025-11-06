"""Test fixtures and stubs for SAML auth tests."""

# backend/tests/conftest.py
# Standard Python Libraries
import importlib
import sys
import types
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, Optional, Tuple, TypedDict, cast

# Third-Party Libraries
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


def _install_fake_django(monkeypatch: Any) -> None:
    """Install a minimal fake Django settings module for imports."""
    fake_django_module: ModuleType = types.ModuleType("django")
    fake_django_conf_module: ModuleType = types.ModuleType("django.conf")

    # Cast to Any so mypy allows arbitrary attributes (attr-defined).
    fake_django_conf_module_any = cast(Any, fake_django_conf_module)
    fake_django_module_any = cast(Any, fake_django_module)

    fake_settings = SimpleNamespace(DEBUG=False)
    fake_django_conf_module_any.settings = fake_settings
    fake_django_module_any.conf = fake_django_conf_module_any

    sys.modules["django"] = fake_django_module
    sys.modules["django.conf"] = fake_django_conf_module


class _FakeUserQuerySet:
    """Provide a tiny QuerySet-like helper used by the fake model manager."""

    def __init__(self, store: Dict[str, "FakeUser"], email_lookup: str) -> None:
        """Initialize the query helper.

        Args:
            store: In-memory user store keyed by email.
            email_lookup: Email value to look up.
        """
        self._store = store
        self._email_lookup = email_lookup


class _FakeUserManager:
    """Stand-in for Django's model manager (email-keyed only)."""

    def __init__(self) -> None:
        """Initialize with an empty in-memory store keyed by email."""
        self._by_email: Dict[str, "FakeUser"] = {}

    def filter(
        self,
        email: Optional[str] = None,
        okta_id__isnull: Any = None,  # pylint: disable=unused-argument
    ) -> _FakeUserQuerySet:
        """Return a fake queryset object; only email lookups are supported."""
        return _FakeUserQuerySet(self._by_email, email or "")

    def get(
        self, okta_id: Any = None, email: Optional[str] = None
    ) -> "FakeUser":  # pylint: disable=unused-argument
        """Return a fake user by email; raise KeyError if not present."""
        if email:
            obj = self._by_email.get(email)
            if obj is None:
                raise KeyError("DoesNotExist")
            return obj
        raise KeyError("DoesNotExist")

    def create(self, **kwargs: Any) -> "FakeUser":
        """Create and store a new user in memory, keyed by email."""
        user = FakeUser(**kwargs)
        user.save()
        return user

    def count(self) -> int:  # pragma: no cover - not used, kept for compatibility
        """Return total count of users in the store."""
        return len(self._by_email)


class FakeUser:
    """Implement an in-memory fake of the `User` model for auth_saml tests."""

    objects = _FakeUserManager()

    def __init__(self, email: str, **kwargs: Any) -> None:
        """Initialize a fake user."""
        self.email = email
        self.first_name = kwargs.get("first_name", "") or ""
        self.last_name = kwargs.get("last_name", "") or ""
        self.user_type = kwargs.get("user_type", "standard")
        self.invite_pending = kwargs.get("invite_pending", True)
        self.can_select_own_state = kwargs.get("can_select_own_state", True)
        self.okta_id = kwargs.get("okta_id")
        self.cognito_username = kwargs.get("cognito_username")
        self.cognito_use_case_description = kwargs.get("cognito_use_case_description")
        self.cognito_email_verified = kwargs.get("cognito_email_verified", False)
        self.cognito_groups = kwargs.get("cognito_groups", [])
        self.last_logged_in = kwargs.get("last_logged_in")
        self.login_blocked_by_maintenance = kwargs.get(
            "login_blocked_by_maintenance", False
        )

    def save(self) -> None:
        """Persist into the in-memory store keyed by email."""
        # pylint: disable=protected-access
        self.__class__.objects._by_email[self.email] = self

    def refresh_from_db(self) -> None:
        """Reload values from the in-memory store (no-op here)."""
        return


def _install_fake_models() -> ModuleType:
    """Install a lightweight in-memory `xfd_mini_dl.models` with a `User` class."""
    fake_models_pkg: ModuleType = types.ModuleType("xfd_mini_dl")
    fake_models_module: ModuleType = types.ModuleType("xfd_mini_dl.models")

    # Cast to Any so mypy allows setting attributes on the module.
    fake_models_module_any = cast(Any, fake_models_module)
    fake_models_pkg_any = cast(Any, fake_models_pkg)

    fake_models_module_any.User = FakeUser
    fake_models_pkg_any.models = fake_models_module

    sys.modules["xfd_mini_dl"] = fake_models_pkg
    sys.modules["xfd_mini_dl.models"] = fake_models_module
    return fake_models_module


def _install_fake_auth() -> ModuleType:
    """Install a fake `xfd_api.auth` module with helpers used by auth_saml."""

    def fake_update_login_block_status(user: Any) -> None:
        """Ensure user is not blocked for maintenance."""
        user.login_blocked_by_maintenance = False

    def fake_create_jwt_token(user: Any) -> str:
        """Return a deterministic token for the given user."""
        return "fake-jwt-for-" + (user.okta_id or user.email)

    def fake_validate_json_serialization(
        obj: Any, label: Optional[str] = None  # pylint: disable=unused-argument
    ) -> None:
        """Perform a no-op JSON validation."""
        return

    def fake_user_to_dict(user: Any) -> Dict[str, Any]:
        """Convert the fake user to a portable dict for responses."""
        return {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_type": user.user_type,
        }

    fake_auth_module: ModuleType = types.ModuleType("xfd_api.auth")
    fake_auth_any = cast(Any, fake_auth_module)
    fake_auth_any.update_login_block_status = fake_update_login_block_status
    fake_auth_any.create_jwt_token = fake_create_jwt_token
    fake_auth_any.validate_json_serialization = fake_validate_json_serialization
    fake_auth_any.user_to_dict = fake_user_to_dict

    if "xfd_api" not in sys.modules:
        sys.modules["xfd_api"] = types.ModuleType("xfd_api")
    sys.modules["xfd_api.auth"] = fake_auth_module
    return fake_auth_module


def _install_fake_onelogin_modules() -> Tuple[ModuleType, ModuleType, ModuleType]:
    """Install fake `onelogin.saml2.*` modules to avoid network/crypto calls."""
    fake_onelogin_pkg: ModuleType = types.ModuleType("onelogin")
    fake_onelogin_saml2_pkg: ModuleType = types.ModuleType("onelogin.saml2")
    fake_onelogin_auth_mod: ModuleType = types.ModuleType("onelogin.saml2.auth")
    fake_onelogin_settings_mod: ModuleType = types.ModuleType("onelogin.saml2.settings")
    fake_onelogin_parser_mod: ModuleType = types.ModuleType(
        "onelogin.saml2.idp_metadata_parser"
    )

    class FakeSettings:
        """Expose a minimal subset of OneLogin settings API used by auth_saml."""

        def __init__(self, settings: Dict[str, Any]) -> None:
            """Store merged settings for later use."""
            self._settings = settings

        def get_sp_metadata(self) -> str:
            """Return a minimal SP metadata XML string for tests."""
            return "<md:EntityDescriptor>test-sp</md:EntityDescriptor>"

        def validate_metadata(self, _metadata: str) -> list[str]:
            """Return an empty list indicating no validation errors."""
            return []

    class FakeAuth:
        """Expose a minimal compatible API for `OneLogin_Saml2_Auth`."""

        def __init__(self, data: Dict[str, Any], old_settings: Any) -> None:
            """Store request data and settings."""
            self.data = data
            self.old_settings = old_settings

        def login(self, return_to: Optional[str] = None) -> str:
            """Return a fake IdP redirect URL that embeds RelayState."""
            relay = return_to or "/"
            return f"https://idp.example.test/sso?RelayState={relay}"

        def process_response(self) -> None:
            """Perform a no-op SAML response processing."""
            return

        def get_errors(self) -> list[str]:
            """Return an empty list indicating success."""
            return []

        def is_authenticated(self) -> bool:
            """Indicate that the user is authenticated."""
            return True

        def get_nameid(self) -> str:
            """Return a deterministic NameID value."""
            return "00u-fake-okta-id"

        def get_attributes(self) -> Dict[str, list[str]]:
            """Return a minimal attribute map for tests."""
            return {
                "email": ["alice@example.com"],
                "given_name": ["Alice"],
                "family_name": ["Testington"],
                "groups": ["standard"],
            }

    class FakeParser:
        """Return canned metadata instead of fetching from the network."""

        @staticmethod
        def parse_remote(url: str) -> Dict[str, Any]:  # pylint: disable=unused-argument
            """Return basic IdP info for the provided metadata URL."""
            return {"idp": {"sso_url": "https://idp.example.test/sso"}}

        @staticmethod
        def merge_settings(
            sp_settings: Dict[str, Any], idp_data: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Merge SP settings with IdP data and return the dict."""
            merged = dict(sp_settings)
            merged.update(idp_data)
            return merged

    # Cast modules to Any so mypy allows assigning attributes.
    auth_any = cast(Any, fake_onelogin_auth_mod)
    settings_any = cast(Any, fake_onelogin_settings_mod)
    parser_any = cast(Any, fake_onelogin_parser_mod)
    onelogin_pkg_any = cast(Any, fake_onelogin_pkg)

    auth_any.OneLogin_Saml2_Auth = FakeAuth
    settings_any.OneLogin_Saml2_Settings = FakeSettings
    parser_any.OneLogin_Saml2_IdPMetadataParser = FakeParser

    # Ensure onelogin.saml2 is reachable as an attribute.
    onelogin_pkg_any.saml2 = fake_onelogin_saml2_pkg

    sys.modules["onelogin"] = fake_onelogin_pkg
    sys.modules["onelogin.saml2"] = fake_onelogin_saml2_pkg
    sys.modules["onelogin.saml2.auth"] = fake_onelogin_auth_mod
    sys.modules["onelogin.saml2.settings"] = fake_onelogin_settings_mod
    sys.modules["onelogin.saml2.idp_metadata_parser"] = fake_onelogin_parser_mod

    return fake_onelogin_auth_mod, fake_onelogin_settings_mod, fake_onelogin_parser_mod


class SamlEnv(TypedDict):
    """Describe the return type for the SAML fixture payload."""

    client: TestClient
    auth_saml: ModuleType
    FakeUser: type[FakeUser]


@pytest.fixture
def saml_test_env(monkeypatch: Any) -> SamlEnv:
    """Set up and return an isolated TestClient + loaded module for SAML tests.

    This fixture:
      * Sets env vars used by `auth_saml`.
      * Installs fake modules for `django`, `xfd_mini_dl.models`, `xfd_api.auth`,
        and `onelogin.saml2.*`.
      * Imports `xfd_api.auth_saml` (after stubs are in place).
      * Mounts its router into a small FastAPI app and returns a TestClient.

    Returns:
        A dict with:
            - client: TestClient
            - auth_saml: the loaded module under test
            - FakeUser: the in-memory model class
    """
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost")
    monkeypatch.setenv("OKTA_SAML_METADATA_URL", "https://example.okta/metadata")

    _install_fake_django(monkeypatch)
    fake_models_module = _install_fake_models()
    _install_fake_auth()
    _install_fake_onelogin_modules()

    # Import the real code under test (now that stubs exist)
    auth_saml = importlib.import_module("xfd_api.auth_saml")

    # Build a tiny app that mounts the router
    app = FastAPI()
    app.include_router(auth_saml.router)
    client = TestClient(app)

    return {
        "client": client,
        "auth_saml": auth_saml,
        # mypy: module attribute access via Any keeps it happy.
        "FakeUser": cast(Any, fake_models_module).User,
    }
