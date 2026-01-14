"""Auth SAML routes for FastAPI backend."""

# Standard Python Libraries
from datetime import datetime, timezone
import logging
import os
import ssl
from typing import Any, Dict, Optional
import urllib.parse
import urllib.request

# Third-Party Libraries
from django.conf import settings as dj_settings
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from xfd_api.helpers.email import ensure_zscaler_cert_downloaded
from xfd_mini_dl.models import User

from .auth import (
    create_jwt_token,
    update_login_block_status,
    user_to_dict,
    validate_json_serialization,
)

LOGGER = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Env helpers & config
# =============================================================================
def _env_truthy(in_var: Optional[str]) -> bool:
    """Return True if an environment variable-like string is truthy."""
    if in_var is None:
        return False
    return in_var.strip().lower() in {"1", "true", "yes", "y", "on"}


def determine_cookie_domain(frontend_domain: str, is_local: bool) -> Optional[str]:
    """Determine the correct cookie domain based on the environment's frontend domain."""
    if is_local:
        return None

    parsed = urllib.parse.urlparse(frontend_domain)
    host = parsed.hostname or ""

    # DMZ environments
    if host.endswith("crossfeed.cyber.dhs.gov"):
        return ".crossfeed.cyber.dhs.gov"
    # LZ environments
    if host.endswith("cisa.dhs.gov"):
        return ".cisa.dhs.gov"

    # Fallback — safest is None (no domain override)
    return None


BACKEND_DOMAIN = (
    os.getenv("BACKEND_DOMAIN") or os.getenv("APP_BASE_URL") or ""
).rstrip("/")
FRONTEND_DOMAIN = (
    os.getenv("FRONTEND_DOMAIN") or os.getenv("FRONTEND_BASE_URL") or ""
).rstrip("/")

# Sourced from environment Django settings
OKTA_METADATA_URL = os.getenv("OKTA_SAML_METADATA_URL")

IS_LOCAL = _env_truthy(os.getenv("IS_LOCAL"))
IS_DMZ = os.getenv("IS_DMZ", "0") == "1"
SAML_SP_CERT = os.getenv("SAML_SP_CERT")
SAML_SP_PRIVATE_KEY = os.getenv("SAML_SP_PRIVATE_KEY")

COOKIE_DOMAIN = determine_cookie_domain(FRONTEND_DOMAIN, IS_LOCAL)


# =============================================================================
# Injectable IdP parser + lazy settings cache to avoid import-time fetch errors
# =============================================================================


class _SamlConfig:
    """Mutable SAML settings holder used to avoid module-level globals."""

    idp_parser = OneLogin_Saml2_IdPMetadataParser
    settings_cache: Optional[Dict[str, Any]] = None


def reset_saml_settings_cache_for_tests() -> None:
    """Clear cached SAML settings for tests."""
    _SamlConfig.settings_cache = None


def set_idp_metadata_parser_for_tests(parser_cls) -> None:
    """Inject a fake IdP metadata parser for tests."""
    _SamlConfig.idp_parser = parser_cls


def _fetch_idp_metadata_lz(url: str) -> bytes:
    """
    Fetch IdP metadata using Zscaler CA bundle.

    Required in LZ environments because outbound HTTPS must use Zscaler CA.
    """
    parsed = urllib.parse.urlparse(url)

    # Must be HTTPS
    if parsed.scheme.lower() != "https":
        raise HTTPException(status_code=400, detail="IdP metadata URL must use https")

    # Must have a hostname (prevents file://, relative paths)
    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Invalid IdP metadata URL")

    cert_path = ensure_zscaler_cert_downloaded()
    # Create SSL context that trusts Zscaler root CA
    ctx = ssl.create_default_context(cafile=cert_path)

    # Explicit metadata fetch (instead of parse_remote)
    with urllib.request.urlopen(url, context=ctx) as resp:  # nosec B310
        return resp.read()


def _build_sp_settings() -> Dict[str, Any]:
    """Build SAML settings dict by merging SP config with Okta IdP metadata."""
    if not OKTA_METADATA_URL:
        raise RuntimeError("OKTA_SAML_METADATA_URL is not set")

    if not IS_DMZ:
        # Fetch metadata using Zscaler CA bundle
        raw_xml = _fetch_idp_metadata_lz(OKTA_METADATA_URL)

        # Parse the XML
        idp_data = _SamlConfig.idp_parser.parse(raw_xml)
    else:
        # Fetch & parse IdP metadata
        idp_data = _SamlConfig.idp_parser.parse_remote(OKTA_METADATA_URL)

    sp_settings: Dict[str, Any] = {
        "strict": False,  # consider True once IdP config is finalized
        "debug": dj_settings.DEBUG,
        "sp": {
            "entityId": f"{BACKEND_DOMAIN}/saml/metadata",
            "assertionConsumerService": {
                "url": f"{BACKEND_DOMAIN}/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": f"{BACKEND_DOMAIN}/saml/logout",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
        },
        "security": {
            "authnRequestsSigned": False,
            "logoutRequestSigned": False,
            "logoutResponseSigned": False,
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
            "wantNameId": True,
            "wantNameIdEncrypted": False,  # toggle local below
            "wantAssertionsEncrypted": False,  # toggle local below
            "requestedAuthnContext": True,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            "relaxDestinationValidation": False,
            "rejectDeprecatedAlgorithm": True,
        },
        "baseurl": f"{BACKEND_DOMAIN}",
        "contactPerson": {},
        "organization": {},
    }

    if IS_LOCAL:
        LOGGER.info("SAML encryption DISABLED (local).")
    else:
        if SAML_SP_CERT:
            # Cert/key are provided directly via environment (PEM strings)
            sp_settings["sp"]["x509cert"] = SAML_SP_CERT.strip()
            if SAML_SP_PRIVATE_KEY:
                sp_settings["sp"]["privateKey"] = SAML_SP_PRIVATE_KEY.strip()
            sp_settings["security"]["wantAssertionsEncrypted"] = True
            sp_settings["security"]["wantNameIdEncrypted"] = True
            sp_settings["security"]["authnRequestsSigned"] = True
            LOGGER.info("SAML encryption ENABLED (inline cert/key configured).")
        else:
            LOGGER.info("No SP cert configured; encryption NOT advertised.")

    # Merge with IdP metadata
    return _SamlConfig.idp_parser.merge_settings(sp_settings, idp_data)


def _get_settings_dict() -> Dict[str, Any]:
    """Return the merged SAML settings (build lazily and cache)."""
    if _SamlConfig.settings_cache is None:
        _SamlConfig.settings_cache = _build_sp_settings()
    return _SamlConfig.settings_cache


# =============================================================================
# OneLogin plumbing
# =============================================================================
def _starlette_to_saml_request(request: Request) -> Dict[str, Any]:
    """Translate FastAPI/Starlette request to python3-saml expected dict."""
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host"),
        "script_name": request.scope.get("root_path", ""),
        "server_port": request.url.port
        or (443 if request.url.scheme == "https" else 80),
        "get_data": dict(request.query_params),
        "post_data": {},  # populated for ACS
    }


def _get_auth(
    request: Request,
    with_post: Optional[dict] = None,
) -> OneLogin_Saml2_Auth:
    """Return a OneLogin_Saml2_Auth instance for the given request."""
    data = _starlette_to_saml_request(request)
    if with_post:
        data["post_data"] = with_post
    settings = OneLogin_Saml2_Settings(settings=_get_settings_dict())
    return OneLogin_Saml2_Auth(data, old_settings=settings)


# =============================================================================
# Helpers
# =============================================================================
def _path_only(raw: Optional[str]) -> str:
    """Return a safe, path-only string that always starts with '/'."""
    val = raw or "/"
    decoded = urllib.parse.unquote(val)
    return decoded if decoded.startswith("/") else "/"


def _extract_identity(auth: OneLogin_Saml2_Auth) -> Dict[str, Any]:
    """Pull identity fields from the SAML assertion."""
    name_id = auth.get_nameid() or ""
    attrs = auth.get_attributes() or {}

    okta_id = (attrs.get("custom:OKTA_ID") or [name_id or ""])[0]
    email = (attrs.get("email") or [None])[0]
    first = (attrs.get("firstName") or attrs.get("given_name") or [""])[0]
    last = (attrs.get("lastName") or attrs.get("family_name") or [""])[0]
    groups = attrs.get("groups") or []

    return {
        "okta_id": okta_id,
        "email": email,
        "first": first,
        "last": last,
        "groups": groups,
    }


def _upsert_user(identity: Dict[str, Any]) -> User:
    """Upsert a User keyed by OktaId, with legacy email attachment path."""
    okta_id = identity["okta_id"]
    email = identity["email"]
    first = identity["first"]
    last = identity["last"]
    groups = identity["groups"]

    # Try to find the user by OktaId first
    user = User.objects.filter(okta_id=okta_id).first()

    if not user:
        # If no user with OktaId exists, try to find a legacy user by email
        user = User.objects.filter(email=email).first()
        if user:
            # Update the legacy user in place
            user.okta_id = okta_id
            user.first_name = user.first_name or (first or None)
            user.last_name = user.last_name or (last or None)
            if user.invite_pending:
                user.invite_pending = False
        else:
            # Create a new user if no legacy user exists
            user = User(
                okta_id=okta_id,
                email=email or None,
                first_name=first or None,
                last_name=last or None,
                user_type="standard",
                invite_pending=True,
                can_select_own_state=True,
            )
    else:
        # Update the existing user with OktaId
        user.first_name = user.first_name or (first or None)
        user.last_name = user.last_name or (last or None)
        if email and user.email != email:
            user.email = email

    # Update additional fields
    user.cognito_username = None
    user.cognito_use_case_description = identity["nickname"]
    user.cognito_email_verified = True
    user.cognito_groups = groups
    user.last_logged_in = datetime.now(timezone.utc)
    user.last_notified_30 = None

    # Update login block status and save the user
    update_login_block_status(user)
    user.save()
    return user


def _redirect_with_cookies(relay: Optional[str], token: str) -> RedirectResponse:
    """Return a 303 redirect to the SPA and set auth cookies."""
    relay_path = _path_only(relay)
    target = f"{FRONTEND_DOMAIN.rstrip('/')}{relay_path}"
    resp = RedirectResponse(target, status_code=303)

    is_https = BACKEND_DOMAIN.startswith("https://")
    # TODO: CRASM-3443 Refactor token usage globally to reduce security risks for XSS.
    # Avoid tokens in localStorage and set cookie flags appropriately for security.
    # Determine need for "token" and "crossfeed-token" and adjust accordingly.

    # Set auth cookies to match current design expectations.
    resp.set_cookie(
        "token",
        token,
        secure=is_https,
        samesite="None" if not IS_LOCAL else "Lax",
        path="/",
        domain=COOKIE_DOMAIN,
    )
    resp.set_cookie(
        "crossfeed-token",
        token,
        secure=is_https,
        samesite="None" if not IS_LOCAL else "Lax",
        path="/",
        domain=COOKIE_DOMAIN,
    )
    return resp


# =============================================================================
# Routes
# =============================================================================
@router.get("/saml/metadata")
def saml_metadata():
    """Return the SAML SP metadata document."""
    settings = OneLogin_Saml2_Settings(settings=_get_settings_dict())
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        raise HTTPException(
            status_code=500,
            detail=f"SP metadata invalid: {', '.join(errors)}",
        )
    return Response(content=metadata, media_type="application/xml")


@router.get("/saml/login")
def saml_login(request: Request, next: str = "/"):
    """
    Start an SP-initiated SAML login.

    Optional `next` controls where the user lands after login.
    """
    next_path = _path_only(request.query_params.get("next"))
    auth = _get_auth(request)
    return RedirectResponse(auth.login(return_to=next_path))


@router.post("/saml/acs")
async def saml_acs(request: Request):
    """Process the SAML response, upsert a user, issue JWT, and set cookies."""
    form = dict(await request.form())
    auth = _get_auth(request, with_post=form)
    auth.process_response()

    errors = auth.get_errors()
    if errors or not auth.is_authenticated():
        raise HTTPException(status_code=401, detail=f"SAML auth failed: {errors}")

    identity = _extract_identity(auth)
    if not identity["okta_id"]:
        raise HTTPException(
            status_code=400,
            detail="No OktaId (NameID/custom:OKTA_ID) in SAML assertion",
        )

    user = _upsert_user(identity)
    token = create_jwt_token(user)

    validate_json_serialization(user_to_dict(user), label="User Dict")

    relay = form.get("RelayState") or "/"
    return _redirect_with_cookies(relay, token)


@router.get("/saml/logout")
def saml_logout(request: Request, next: str = "/"):
    """Log the user out of the app and clear auth cookies."""
    next_path = _path_only(request.query_params.get("next"))
    target = f"{FRONTEND_DOMAIN.rstrip('/')}{next_path}"
    resp = RedirectResponse(target, status_code=303)
    resp.delete_cookie("token", path="/")
    resp.delete_cookie("crossfeed-token", path="/")
    return resp
