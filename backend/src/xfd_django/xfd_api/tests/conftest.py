"""Test fixtures for SAML auth tests."""
# backend/tests/conftest.py
# Standard Python Libraries
import importlib
import sys
import types

# Third-Party Libraries
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def saml_test_env(monkeypatch):
    """
    Build a fully isolated test environment for the SAML endpoints.

    We:
    - stub out django.conf.settings (so importing auth_saml won't try to load real Django)
    - stub out xfd_mini_dl.models.User (so no real DB)
    - stub out xfd_api.auth helpers (so no real JWT logic needed)
    - stub out onelogin.saml2.* classes (so no network/crypto calls)
    - set the env vars that auth_saml expects
    - import xfd_api.auth_saml AFTER all the stubs are in place
    - mount its router on a FastAPI app and return a TestClient + module ref
    """
    #
    # 1. Env vars expected by auth_saml
    #
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost")
    monkeypatch.setenv("OKTA_SAML_METADATA_URL", "https://example.okta/metadata")

    #
    # 2. Fake django.conf.settings
    #
    fake_django_module = types.ModuleType("django")
    fake_django_conf_module = types.ModuleType("django.conf")
    # django.conf.settings is what auth_saml imports as dj_settings
    fake_settings = types.SimpleNamespace(DEBUG=False)
    fake_django_conf_module.settings = fake_settings
    fake_django_module.conf = fake_django_conf_module

    sys.modules["django"] = fake_django_module
    sys.modules["django.conf"] = fake_django_conf_module

    #
    # 3. Fake xfd_mini_dl.models with a lightweight in-memory User model
    #
    class _FakeUserQuerySet:
        def __init__(self, store, email_lookup):
            self._store = store
            self._email_lookup = email_lookup

        def first(self):
            # Return either the found user or None
            return self._store.get(self._email_lookup)

    class _FakeUserManager:
        def __init__(self):
            # keyed by email
            self._by_email = {}

        def filter(self, email=None):
            return _FakeUserQuerySet(self._by_email, email)

    class FakeUser:
        objects = _FakeUserManager()

        def __init__(
            self,
            email,
            first_name=None,
            last_name=None,
            user_type="standard",
            invite_pending=True,
            can_select_own_state=True,
        ):
            self.email = email
            self.first_name = first_name or ""
            self.last_name = last_name or ""
            self.user_type = user_type
            self.invite_pending = invite_pending
            self.can_select_own_state = can_select_own_state
            self.okta_id = None
            self.cognito_username = None
            self.cognito_use_case_description = None
            self.cognito_email_verified = False
            self.cognito_groups = []
            self.last_logged_in = None

            # maintenance flag that update_login_block_status might touch
            self.login_blocked_by_maintenance = False

        def save(self):
            # "persist" in memory by email
            self.__class__.objects._by_email[self.email] = self

    fake_models_pkg = types.ModuleType("xfd_mini_dl")
    fake_models_module = types.ModuleType("xfd_mini_dl.models")
    fake_models_module.User = FakeUser
    fake_models_pkg.models = fake_models_module

    sys.modules["xfd_mini_dl"] = fake_models_pkg
    sys.modules["xfd_mini_dl.models"] = fake_models_module

    #
    # 4. Fake xfd_api.auth helper module
    #
    def fake_update_login_block_status(user):
        # could set user.login_blocked_by_maintenance = True if you ever
        # want to simulate a maintenance lockout
        user.login_blocked_by_maintenance = False

    def fake_create_jwt_token(user):
        # Return something deterministic
        return "fake-jwt-for-" + (user.okta_id or user.email)

    def fake_validate_json_serialization(obj, label=None):
        # no-op in tests
        return

    def fake_user_to_dict(user):
        return {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_type": user.user_type,
        }

    fake_auth_module = types.ModuleType("xfd_api.auth")
    fake_auth_module.update_login_block_status = fake_update_login_block_status
    fake_auth_module.create_jwt_token = fake_create_jwt_token
    fake_auth_module.validate_json_serialization = fake_validate_json_serialization
    fake_auth_module.user_to_dict = fake_user_to_dict

    # We also have to register the parent package xfd_api if not loaded yet.
    if "xfd_api" not in sys.modules:
        sys.modules["xfd_api"] = types.ModuleType("xfd_api")

    sys.modules["xfd_api.auth"] = fake_auth_module

    #
    # 5. Fake onelogin.saml2.* classes so importing auth_saml doesn't
    #    try to talk to real IdP metadata or do XML crypto.
    #
    fake_onelogin_pkg = types.ModuleType("onelogin")
    fake_onelogin_saml2_pkg = types.ModuleType("onelogin.saml2")
    fake_onelogin_auth_mod = types.ModuleType("onelogin.saml2.auth")
    fake_onelogin_settings_mod = types.ModuleType("onelogin.saml2.settings")
    fake_onelogin_parser_mod = types.ModuleType("onelogin.saml2.idp_metadata_parser")

    class FakeSettings:
        def __init__(self, settings):
            # store merged settings
            self._settings = settings

        def get_sp_metadata(self):
            # minimal SP metadata XML string
            return "<md:EntityDescriptor>test-sp</md:EntityDescriptor>"

        def validate_metadata(self, _metadata):
            # no validation errors
            return []

    class FakeAuth:
        """
        Patch auth_saml._get_auth later in each test.

        This will return an instance of a subclass of this with
        test-specific behavior. This base class just documents shape.
        """

        def __init__(self, data, old_settings):
            self.data = data
            self.old_settings = old_settings

        def login(self, return_to=None):
            # SAML redirect URL (IdP) we "would" send user to
            relay = return_to or "/"
            return f"https://idp.example.test/sso?RelayState={relay}"

        def process_response(self):
            pass

        def get_errors(self):
            return []

        def is_authenticated(self):
            return True

        def get_nameid(self):
            return "00u-fake-okta-id"

        def get_attributes(self):
            return {
                "email": ["alice@example.com"],
                "given_name": ["Alice"],
                "family_name": ["Testington"],
                "groups": ["standard"],
            }

    class FakeParser:
        @staticmethod
        def parse_remote(url):
            # simulate parsing Okta metadata URL
            return {"idp": {"sso_url": "https://idp.example.test/sso"}}

        @staticmethod
        def merge_settings(sp_settings, idp_data):
            merged = dict(sp_settings)
            merged.update(idp_data)
            return merged

    fake_onelogin_auth_mod.OneLogin_Saml2_Auth = FakeAuth
    fake_onelogin_settings_mod.OneLogin_Saml2_Settings = FakeSettings
    fake_onelogin_parser_mod.OneLogin_Saml2_IdPMetadataParser = FakeParser

    fake_onelogin_pkg.saml2 = fake_onelogin_saml2_pkg

    # register these fake modules so that "from onelogin.saml2.auth import OneLogin_Saml2_Auth" works
    sys.modules["onelogin"] = fake_onelogin_pkg
    sys.modules["onelogin.saml2"] = fake_onelogin_saml2_pkg
    sys.modules["onelogin.saml2.auth"] = fake_onelogin_auth_mod
    sys.modules["onelogin.saml2.settings"] = fake_onelogin_settings_mod
    sys.modules["onelogin.saml2.idp_metadata_parser"] = fake_onelogin_parser_mod

    #
    # 6. Now that all stubs are ready, import the real code-under-test
    #
    auth_saml = importlib.import_module("xfd_api.auth_saml")

    #
    # 7. Build a tiny FastAPI app that mounts the router from auth_saml
    #
    app = FastAPI()
    app.include_router(auth_saml.router)

    client = TestClient(app)

    #
    # 8. Return everything tests will need
    #
    return {
        "client": client,
        "auth_saml": auth_saml,
        "FakeUser": fake_models_module.User,
    }
