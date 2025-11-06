"""Tests for SAML authentication endpoints."""

# Standard Python Libraries
from importlib import reload

# Third-Party Libraries
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

# Local Libraries
from xfd_mini_dl.models import User

FAKE_IDP_DATA = {
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
    }
}


class _FakeAuthOK:
    """Happy-path fake of OneLogin_Saml2_Auth used in ACS & login tests."""

    def __init__(self, data, old_settings=None):
        """Initialize with request data and the old settings instance."""
        self.data = data
        self.old_settings = old_settings
        self._attrs = {
            # Simulate Okta attributes.
            "custom:OKTA_ID": ["00uFAKEID1234567890"],
            "email": ["user@example.gov"],
            "given_name": ["Test"],
            "family_name": ["User"],
            # Add groups if needed:
            # "groups": ["groupA", "groupB"],
        }

    # === login (SP-initiated) ===
    def login(self, return_to=None):
        """Generate a fake IdP redirect URL that includes RelayState."""
        return f"https://idp.example.com/sso?return_to={return_to or '/'}"

    # === ACS (IdP-POST) ===
    def process_response(self):
        """No-op process response for happy path."""
        return None

    def get_errors(self):
        """Return an empty list for no errors."""
        return []

    def is_authenticated(self):
        """Return authenticated in happy path."""
        return True

    def get_nameid(self):
        """Return a deterministic fake NameID."""
        return "00uFAKEID1234567890"

    def get_attributes(self):
        """Return the fake attributes map."""
        return self._attrs


def _mount_client(monkeypatch, *, env: dict):
    """Create a TestClient with patched environment and IdP metadata.

    This helper:
    - Sets environment variables for the module under test.
    - Patches OneLogin_Saml2_IdPMetadataParser.parse_remote to avoid network.
    - Reloads the auth_saml module so settings are rebuilt.
    - Mounts a minimal FastAPI app including the SAML router.

    Returns:
        (client, saml_mod): A tuple of the TestClient and the reloaded module.
    """
    # Set environment for this test.
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))

    # Import here so we can patch after reload.
    # Third-Party Libraries
    import xfd_api.auth_saml as saml_mod  # type: ignore

    # Mock the IdP metadata fetch/parse to avoid external calls.
    monkeypatch.setattr(
        saml_mod.OneLogin_Saml2_IdPMetadataParser,  # type: ignore[attr-defined]
        "parse_remote",
        lambda url: FAKE_IDP_DATA,
    )

    # Reload so SAML_SETTINGS_DATA is rebuilt with the fresh env & patched parser.
    saml_mod = reload(saml_mod)

    # Build a tiny app with only the SAML router.
    app = FastAPI()
    app.include_router(saml_mod.router)
    client = TestClient(app)
    return client, saml_mod


@pytest.mark.django_db
def test_login_redirect_uses_path_only_relaystate(monkeypatch):
    """/saml/login redirects to IdP using a path-only RelayState.

    The backend should pass a path-only RelayState into OneLogin login()
    and return a redirect to the IdP URL with that RelayState.
    """
    client, saml_mod = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "APP_BASE_URL": "http://localhost:3000",
            "FRONTEND_BASE_URL": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
        },
    )

    # Replace the Auth class with our fake to capture return_to behavior.
    monkeypatch.setattr(saml_mod, "OneLogin_Saml2_Auth", _FakeAuthOK)

    r = client.get("/saml/login", params={"next": "/inventory"})
    # FastAPI RedirectResponse default is 307; on some stacks it can be 302.
    assert r.status_code in (302, 307)
    assert "https://idp.example.com/sso?return_to=/inventory" in r.headers["location"]


@pytest.mark.django_db(transaction=True)
def test_acs_creates_user_by_okta_id_sets_cookies_and_redirect(monkeypatch):
    """POST /saml/acs creates user by okta_id, sets cookies, and 303s to SPA.

    The ACS handler should:
    - Upsert the user by OktaId.
    - Issue a JWT and set cookies.
    - Redirect with 303 to the SPA root (POST->GET).
    """
    client, saml_mod = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "APP_BASE_URL": "http://localhost:3000",
            "FRONTEND_BASE_URL": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
        },
    )

    # Fake SAML class & helper funcs.
    monkeypatch.setattr(saml_mod, "OneLogin_Saml2_Auth", _FakeAuthOK)
    monkeypatch.setattr(saml_mod, "create_jwt_token", lambda u: "TESTTOKEN")
    monkeypatch.setattr(saml_mod, "update_login_block_status", lambda u: None)

    # No user exists yet.
    assert User.objects.filter(okta_id="00uFAKEID1234567890").count() == 0

    # Simulate IdP POST to ACS.
    r = client.post("/saml/acs", data={"RelayState": "/"})
    # 303 so POST->GET for SPA navigation.
    assert r.status_code == 303
    assert r.headers["location"] == "http://localhost/"

    # Cookies present (look at combined Set-Cookie header).
    set_cookie = r.headers.get("set-cookie", "")
    assert "token=" in set_cookie
    assert "crossfeed-token=" in set_cookie

    # User created with okta_id set.
    user = User.objects.get(okta_id="00uFAKEID1234567890")
    assert user.email == "user@example.gov"
    assert user.first_name == "Test"
    assert user.last_name == "User"


@pytest.mark.django_db(transaction=True)
def test_acs_attaches_legacy_user_by_email(monkeypatch):
    """POST /saml/acs attaches okta_id to legacy user matched by email.

    If a legacy user exists with a matching email and no okta_id,
    ACS should attach the okta_id to that user rather than creating a new one.
    """
    # Pre-create legacy user.
    legacy = User.objects.create(
        email="user@example.gov",
        first_name="",
        last_name="",
        user_type="standard",
        invite_pending=True,
        can_select_own_state=True,
    )

    client, saml_mod = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "APP_BASE_URL": "http://localhost:3000",
            "FRONTEND_BASE_URL": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
        },
    )

    monkeypatch.setattr(saml_mod, "OneLogin_Saml2_Auth", _FakeAuthOK)
    monkeypatch.setattr(saml_mod, "create_jwt_token", lambda u: "TESTTOKEN")
    monkeypatch.setattr(saml_mod, "update_login_block_status", lambda u: None)

    r = client.post("/saml/acs", data={"RelayState": "/VSDashboard"})
    assert r.status_code == 303
    assert r.headers["location"] == "http://localhost/VSDashboard"

    # The same legacy user should now have okta_id set (no new user).
    legacy.refresh_from_db()
    assert legacy.okta_id == "00uFAKEID1234567890"
    assert User.objects.filter(email="user@example.gov").count() == 1


@pytest.mark.django_db
def test_metadata_local_no_encryption_keydescriptor(monkeypatch, tmp_path):
    """Local mode: metadata should NOT include an encryption KeyDescriptor."""
    client, _ = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "1",
            "APP_BASE_URL": "http://localhost:3000",
            "FRONTEND_BASE_URL": "http://localhost",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
            # No certs in local mode
            "SAML_SP_CERT_PATH": None,
            "SAML_SP_PRIVATE_KEY_PATH": None,
        },
    )
    resp = client.get("/saml/metadata")
    assert resp.status_code == 200
    xml = resp.text
    assert '<KeyDescriptor use="encryption"' not in xml
    assert "BEGIN CERTIFICATE" not in xml


@pytest.mark.django_db
def test_metadata_prod_with_encryption_descriptor_using_cert_only(
    monkeypatch, tmp_path
):
    """Deployed mode: metadata includes KeyDescriptor when a public cert is supplied."""
    sp_cert_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIFakeCertPEMForTestOnly==\n"
        "-----END CERTIFICATE-----\n"
    )
    cert_path = tmp_path / "sp.crt"
    cert_path.write_text(sp_cert_pem)

    client, _ = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "false",
            "APP_BASE_URL": "https://sp.example.gov",
            "FRONTEND_BASE_URL": "https://spa.example.gov",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
            "SAML_SP_CERT_PATH": str(cert_path),
            # Intentionally omit the private key env var
            "SAML_SP_PRIVATE_KEY_PATH": None,
        },
    )

    resp = client.get("/saml/metadata")
    assert resp.status_code == 200
    xml = resp.text
    assert '<KeyDescriptor use="encryption"' in xml
    assert "BEGIN CERTIFICATE" in xml
    assert "MIIFakeCertPEMForTestOnly" in xml


@pytest.mark.django_db
def test_metadata_no_encryption_when_cert_missing(monkeypatch, tmp_path):
    """No cert present: metadata must NOT advertise encryption."""
    client, _ = _mount_client(
        monkeypatch,
        env={
            "IS_LOCAL": "false",
            "APP_BASE_URL": "https://sp.example.gov",
            "FRONTEND_BASE_URL": "https://spa.example.gov",
            "OKTA_SAML_METADATA_URL": "https://idp.example.com/metadata",
            "SAML_SP_CERT_PATH": None,
            "SAML_SP_PRIVATE_KEY_PATH": None,
        },
    )
    resp = client.get("/saml/metadata")
    assert resp.status_code == 200
    xml = resp.text
    assert '<KeyDescriptor use="encryption"' not in xml
