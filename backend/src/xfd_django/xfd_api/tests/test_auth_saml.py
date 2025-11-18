"""Tests for SAML authentication endpoints (no real DB / network)."""

from __future__ import annotations

# Standard Python Libraries
from importlib import reload
from typing import Any

# Third-Party Libraries
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

# ---------------------------------------------------------------------------
# Fake User manager + queryset (pure in-memory, no Django)
# ---------------------------------------------------------------------------


class FakeQuerySet:
    """Tiny stand-in for queryset ops used in auth_saml (_upsert_user)."""

    def __init__(self, objs: list[FakeUser]) -> None:
        """Initialize the fake queryset with a list of users."""
        self._objs = list(objs)

    def first(self) -> FakeUser | None:
        """Return the first user in the queryset or None."""
        return self._objs[0] if self._objs else None

    def count(self) -> int:
        """Return the number of users in the queryset."""
        return len(self._objs)


class FakeUserManager:
    """Very small QuerySet-like manager to back FakeUser.objects."""

    def __init__(self) -> None:
        """Initialize the fake user manager with an empty in-memory store."""
        self._store: list[FakeUser] = []

    def _matches(self, user: FakeUser, **kwargs: Any) -> bool:
        """Return True if the given user matches the provided filters."""
        for key, value in kwargs.items():
            if key.endswith("__isnull"):
                field = key[:-8]
                is_null = getattr(user, field) is None
                if is_null != bool(value):
                    return False
            else:
                if getattr(user, key) != value:
                    return False
        return True

    def filter(self, **kwargs: Any) -> FakeQuerySet:
        """Return a FakeQuerySet of users matching the provided filters."""
        return FakeQuerySet([u for u in self._store if self._matches(u, **kwargs)])

    def create(self, **kwargs: Any) -> FakeUser:
        """Create and store a new FakeUser instance."""
        u = FakeUser(**kwargs)
        if u not in self._store:
            self._store.append(u)
        return u

    def get(self, **kwargs: Any) -> FakeUser:
        """Return a single FakeUser matching the filters or raise KeyError."""
        matches = [u for u in self._store if self._matches(u, **kwargs)]
        if not matches:
            raise KeyError("DoesNotExist")
        if len(matches) > 1:
            raise AssertionError("Multiple objects returned")
        return matches[0]


# ---------------------------------------------------------------------------
# Fake User model (now that manager exists)
# ---------------------------------------------------------------------------


class FakeUser:
    """In-memory stand-in for xfd_mini_dl.models.User."""

    # class-level manager, just like Django's Model.objects
    objects: FakeUserManager = FakeUserManager()

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a fake user instance with typical User fields."""
        self.okta_id = kwargs.get("okta_id")
        self.email = kwargs.get("email")
        self.first_name = kwargs.get("first_name", "") or ""
        self.last_name = kwargs.get("last_name", "") or ""
        self.user_type = kwargs.get("user_type", "standard")
        self.invite_pending = kwargs.get("invite_pending", True)
        self.can_select_own_state = kwargs.get("can_select_own_state", True)
        self.cognito_username = kwargs.get("cognito_username")
        self.cognito_use_case_description = kwargs.get("cognito_use_case_description")
        self.cognito_email_verified = kwargs.get("cognito_email_verified", False)
        self.cognito_groups = kwargs.get("cognito_groups", [])
        self.last_logged_in = kwargs.get("last_logged_in")
        self.login_blocked_by_maintenance = kwargs.get(
            "login_blocked_by_maintenance", False
        )

    def save(self) -> None:
        """Persist this instance into the in-memory manager."""
        mgr = self.__class__.objects
        if self not in mgr._store:
            mgr._store.append(self)

    def refresh_from_db(self) -> None:  # pragma: no cover - no-op
        """Refresh the instance from storage (no-op for fake users)."""
        return


# ---------------------------------------------------------------------------
# Fake OneLogin auth + settings + metadata parser (no network / crypto)
# ---------------------------------------------------------------------------

FAKE_IDP_DATA: dict[str, Any] = {
    "idp": {
        "singleSignOnService": {
            "url": "https://idp.example.com/sso",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
        },
        "singleLogoutService": {
            "url": "https://idp.example.com/slo",
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
        },
        "x509cert": "IDP_CERT_FAKE",
        "entityId": "https://idp.example.com/metadata",
    }
}


class _FakeAuthOK:
    """Happy-path fake of OneLogin_Saml2_Auth used in ACS & login tests."""

    def __init__(self, data: dict[str, Any], old_settings: Any = None) -> None:
        """Initialize the fake SAML auth object with fixed attributes."""
        self.data = data
        self.old_settings = old_settings
        self._attrs = {
            "custom:OKTA_ID": ["00uFAKEID1234567890"],
            "email": ["user@example.gov"],
            "given_name": ["Test"],
            "family_name": ["User"],
        }

    def login(self, return_to: str | None = None) -> str:
        """Return a redirect URL to the fake IdP SSO endpoint."""
        return f"https://idp.example.com/sso?return_to={return_to or '/'}"

    def process_response(self) -> None:
        """Simulate processing a SAML response (no-op)."""
        return

    def get_errors(self) -> list[str]:
        """Return an empty list to indicate no SAML errors."""
        return []

    def is_authenticated(self) -> bool:
        """Return True to indicate the user is authenticated."""
        return True

    def get_nameid(self) -> str:
        """Return a fixed fake NameID value."""
        return "00uFAKEID1234567890"

    def get_attributes(self) -> dict[str, list[str]]:
        """Return the fixed attribute set for the fake user."""
        return self._attrs


class _FakeSettings:
    """Fake OneLogin_Saml2_Settings for metadata tests."""

    def __init__(self, settings: dict[str, Any]) -> None:
        """Initialize fake SAML settings with the given config dict."""
        self._settings = settings

    def get_sp_metadata(self) -> str:
        """Return a minimal SP metadata XML string with optional KeyDescriptor."""
        base = "<md:EntityDescriptor>"
        x509 = self._settings.get("sp", {}).get("x509cert")
        if x509:
            # Emit an encryption KeyDescriptor if a cert is present.
            return (
                f'{base}<KeyDescriptor use="encryption">'
                "-----BEGIN CERTIFICATE-----\n"
                "MIIFakeCertPEMForTestOnly==\n"
                "-----END CERTIFICATE-----\n"
                "</KeyDescriptor></md:EntityDescriptor>"
            )
        return f"{base}test-sp</md:EntityDescriptor>"

    def validate_metadata(self, _metadata: str) -> list[str]:
        """Return an empty list to signal valid SP metadata."""
        return []


# ---------------------------------------------------------------------------
# Helper to mount a tiny FastAPI app for each test
# ---------------------------------------------------------------------------


def _mount_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    env: dict[str, Any],
):
    """Create a TestClient wired to the SAML router with test-only fakes.

    Steps:
      1) Set env variables
      2) Import and reload the auth_saml module
      3) Reset the module's lazy SAML settings cache
      4) Inject a fake IdP metadata parser to avoid the network
      5) Patch User to use FakeUser + in-memory manager
      6) Patch user_to_dict / validate_json_serialization to avoid Django
      7) Build a FastAPI app including the SAML router
    """
    # 1) Env
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))

    if "APP_BASE_URL" in env and "BACKEND_DOMAIN" not in env:
        monkeypatch.setenv("BACKEND_DOMAIN", env["APP_BASE_URL"])
    if "FRONTEND_BASE_URL" in env and "FRONTEND_DOMAIN" not in env:
        monkeypatch.setenv("FRONTEND_DOMAIN", env["FRONTEND_BASE_URL"])

    # 2) Import & reload
    # Third-Party Libraries
    import xfd_api.auth_saml as saml_mod  # type: ignore

    saml_mod = reload(saml_mod)

    # 3) Clear lazy cache
    if hasattr(saml_mod, "reset_saml_settings_cache_for_tests"):
        saml_mod.reset_saml_settings_cache_for_tests()

    # 4) Inject fake IdP parser so no network access
    class _FakeParserLocal:
        """Fake IdP metadata parser used to avoid real HTTP calls."""

        @staticmethod
        def parse_remote(url: str) -> dict[str, Any]:  # noqa: ARG003
            """Return canned IdP metadata regardless of the URL."""
            return FAKE_IDP_DATA

        @staticmethod
        def merge_settings(
            sp_settings: dict[str, Any],
            idp_data: dict[str, Any],
        ) -> dict[str, Any]:
            """Merge SP and IdP dictionaries into a single settings dict."""
            merged = dict(sp_settings)
            merged.update(idp_data)
            return merged

    if hasattr(saml_mod, "set_idp_metadata_parser_for_tests"):
        saml_mod.set_idp_metadata_parser_for_tests(_FakeParserLocal)

    # Use fake OneLogin settings for metadata
    monkeypatch.setattr(
        saml_mod,
        "OneLogin_Saml2_Settings",
        _FakeSettings,
        raising=False,
    )

    # 5) Patch User model to use our in-memory FakeUser
    #    Reset manager store for each test run.
    FakeUser.objects = FakeUserManager()
    fake_manager = FakeUser.objects

    monkeypatch.setattr(saml_mod, "User", FakeUser, raising=False)

    # 6) Patch user_to_dict and validate_json_serialization
    def _fake_user_to_dict(user: FakeUser) -> dict[str, Any]:
        """Return a JSON-serializable dict representing the fake user."""
        return {
            "email": getattr(user, "email", None),
            "first_name": getattr(user, "first_name", None),
            "last_name": getattr(user, "last_name", None),
            "user_type": getattr(user, "user_type", None),
            "okta_id": getattr(user, "okta_id", None),
        }

    monkeypatch.setattr(
        saml_mod,
        "user_to_dict",
        _fake_user_to_dict,
        raising=False,
    )
    monkeypatch.setattr(
        saml_mod,
        "validate_json_serialization",
        lambda obj, label=None: None,
        raising=False,
    )

    # 7) Build app
    app = FastAPI()
    app.include_router(saml_mod.router)
    client = TestClient(app)
    return client, saml_mod, fake_manager


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_login_redirect_uses_path_only_relaystate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that /saml/login redirects using a path-only RelayState."""
    client, saml_mod, _ = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "BACKEND_DOMAIN": "http://localhost:3000",
            "FRONTEND_DOMAIN": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
        },
    )

    # Use our happy-path fake SAML auth
    monkeypatch.setattr(
        saml_mod,
        "OneLogin_Saml2_Auth",
        _FakeAuthOK,
        raising=False,
    )

    # Don't follow redirects to the IdP
    r = client.get(
        "/saml/login",
        params={"next": "/inventory"},
        follow_redirects=False,
    )

    assert r.status_code in (302, 307)
    assert "https://idp.example.com/sso?return_to=/inventory" in r.headers["location"]


def test_acs_creates_user_by_okta_id_sets_cookies_and_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that ACS upserts by okta_id, sets cookies, and redirects."""
    client, saml_mod, user_manager = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "BACKEND_DOMAIN": "http://localhost:3000",
            "FRONTEND_DOMAIN": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
        },
    )

    monkeypatch.setattr(saml_mod, "OneLogin_Saml2_Auth", _FakeAuthOK, raising=False)
    monkeypatch.setattr(
        saml_mod,
        "create_jwt_token",
        lambda u: "TESTTOKEN",
        raising=False,
    )
    monkeypatch.setattr(
        saml_mod,
        "update_login_block_status",
        lambda u: None,
        raising=False,
    )

    assert user_manager.filter(okta_id="00uFAKEID1234567890").count() == 0

    r = client.post("/saml/acs", data={"RelayState": "/"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "http://localhost/"

    set_cookie = r.headers.get("set-cookie", "")
    assert "token=" in set_cookie
    assert "crossfeed-token=" in set_cookie

    # Proves lookup by okta_id works
    user = user_manager.get(okta_id="00uFAKEID1234567890")
    assert user.email == "user@example.gov"
    assert user.first_name == "Test"
    assert user.last_name == "User"


def test_acs_attaches_legacy_user_by_email(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that ACS attaches a legacy user by email instead of duplicating."""
    client, saml_mod, user_manager = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "BACKEND_DOMAIN": "http://localhost:3000",
            "FRONTEND_DOMAIN": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
        },
    )

    # Pre-create legacy user (email only, no okta_id)
    legacy = user_manager.create(
        email="user@example.gov",
        first_name="",
        last_name="",
        user_type="standard",
        invite_pending=True,
        can_select_own_state=True,
    )

    monkeypatch.setattr(saml_mod, "OneLogin_Saml2_Auth", _FakeAuthOK, raising=False)
    monkeypatch.setattr(
        saml_mod,
        "create_jwt_token",
        lambda u: "TESTTOKEN",
        raising=False,
    )
    monkeypatch.setattr(
        saml_mod,
        "update_login_block_status",
        lambda u: None,
        raising=False,
    )

    r = client.post(
        "/saml/acs",
        data={"RelayState": "/VSDashboard"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "http://localhost/VSDashboard"

    # Email-based attach happens instead of creating a duplicate
    assert legacy.okta_id == "00uFAKEID1234567890"
    assert user_manager.filter(email="user@example.gov").count() == 1
    # Same object is retrievable by okta_id too
    same = user_manager.get(okta_id="00uFAKEID1234567890")
    assert same is legacy


def test_metadata_local_no_encryption_keydescriptor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,  # noqa: ARG001
) -> None:
    """Test that local metadata does not advertise encryption KeyDescriptor."""
    client, _, _ = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "BACKEND_DOMAIN": "http://localhost:3000",
            "FRONTEND_DOMAIN": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
            "SAML_SP_CERT_PATH": None,
            "SAML_SP_PRIVATE_KEY_PATH": None,
        },
    )

    resp = client.get("/saml/metadata")
    assert resp.status_code == 200
    xml = resp.text
    assert '<KeyDescriptor use="encryption"' not in xml
    assert "BEGIN CERTIFICATE" not in xml


def test_metadata_prod_with_encryption_descriptor_using_cert_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Test that prod metadata includes encryption KeyDescriptor when cert is set."""
    sp_cert_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIFakeCertPEMForTestOnly==\n"
        "-----END CERTIFICATE-----\n"
    )
    cert_path = tmp_path / "sp.crt"
    cert_path.write_text(sp_cert_pem)

    client, _, _ = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "false",
            "BACKEND_DOMAIN": "https://sp.example.gov",
            "FRONTEND_DOMAIN": "https://spa.example.gov",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
            "SAML_SP_CERT_PATH": str(cert_path),
            "SAML_SP_PRIVATE_KEY_PATH": None,
        },
    )

    resp = client.get("/saml/metadata")
    assert resp.status_code == 200
    xml = resp.text
    assert '<KeyDescriptor use="encryption"' in xml
    assert "BEGIN CERTIFICATE" in xml
    assert "MIIFakeCertPEMForTestOnly" in xml


def test_metadata_no_encryption_when_cert_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,  # noqa: ARG001
) -> None:
    """Test that metadata does not advertise encryption when no cert is present."""
    client, _, _ = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "false",
            "BACKEND_DOMAIN": "https://sp.example.gov",
            "FRONTEND_DOMAIN": "https://spa.example.gov",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
            "SAML_SP_CERT_PATH": None,
            "SAML_SP_PRIVATE_KEY_PATH": None,
        },
    )

    resp = client.get("/saml/metadata")
    assert resp.status_code == 200
    xml = resp.text
    assert '<KeyDescriptor use="encryption"' not in xml
