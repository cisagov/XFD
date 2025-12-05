"""Auth SAML routes for FastAPI backend."""

# Standard Python Libraries
from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, Optional
import urllib.parse

# Third-Party Libraries
from django.conf import settings as dj_settings
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
from onelogin.saml2.settings import OneLogin_Saml2_Settings
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


BACKEND_DOMAIN = (
    os.getenv("BACKEND_DOMAIN") or os.getenv("APP_BASE_URL") or ""
).rstrip("/")
FRONTEND_DOMAIN = (
    os.getenv("FRONTEND_DOMAIN") or os.getenv("FRONTEND_BASE_URL") or ""
).rstrip("/")

# Sourced from environment Django settings
OKTA_METADATA_URL = os.getenv("OKTA_SAML_METADATA_URL")

IS_LOCAL = _env_truthy(os.getenv("IS_LOCAL"))
SAML_SP_CERT = os.getenv("SAML_SP_CERT")
SAML_SP_PRIVATE_KEY = os.getenv("SAML_SP_PRIVATE_KEY")

LOGGER.info(
    "SAML init: BACKEND_DOMAIN='%s', FRONTEND_DOMAIN='%s', IS_LOCAL=%s, "
    "OKTA_METADATA_URL set=%s",
    BACKEND_DOMAIN or "<unset>",
    FRONTEND_DOMAIN or "<unset>",
    IS_LOCAL,
    bool(OKTA_METADATA_URL),
)


# =============================================================================
# Injectable IdP parser + lazy settings cache to avoid import-time fetch errors
# =============================================================================


class _SamlConfig:
    """Mutable SAML settings holder used to avoid module-level globals."""

    idp_parser = OneLogin_Saml2_IdPMetadataParser
    settings_cache: Optional[Dict[str, Any]] = None


def reset_saml_settings_cache_for_tests() -> None:
    """Clear cached SAML settings for tests."""
    LOGGER.info("Resetting SAML settings cache (tests).")
    _SamlConfig.settings_cache = None


def set_idp_metadata_parser_for_tests(parser_cls) -> None:
    """Inject a fake IdP metadata parser for tests."""
    LOGGER.info("Overriding IdP metadata parser for tests: %s", parser_cls)
    _SamlConfig.idp_parser = parser_cls


def _build_sp_settings() -> Dict[str, Any]:
    """Build SAML settings dict by merging SP config with Okta IdP metadata."""
    if not OKTA_METADATA_URL:
        LOGGER.error("OKTA_SAML_METADATA_URL is not set; cannot build SAML settings.")
        raise RuntimeError("OKTA_SAML_METADATA_URL is not set")

    LOGGER.info(
        "Building SAML SP settings from IdP metadata URL: %s", OKTA_METADATA_URL
    )

    # Fetch & parse IdP metadata
    try:
        idp_data = _SamlConfig.idp_parser.parse_remote(OKTA_METADATA_URL)
        LOGGER.info("Successfully parsed IdP metadata from %s", OKTA_METADATA_URL)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception(
            "Failed to parse IdP metadata from %s: %s", OKTA_METADATA_URL, exc
        )
        raise

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
            LOGGER.info(
                "SAML encryption ENABLED (inline cert/key configured; authnRequestsSigned=True)."
            )
        else:
            LOGGER.info("No SP cert configured; encryption NOT advertised.")

    # Merge with IdP metadata
    merged = _SamlConfig.idp_parser.merge_settings(sp_settings, idp_data)
    LOGGER.info(
        "Merged SAML settings built: entityId=%s, acs_url=%s",
        merged.get("sp", {}).get("entityId"),
        merged.get("sp", {}).get("assertionConsumerService", {}).get("url"),
    )
    return merged


def _get_settings_dict() -> Dict[str, Any]:
    """Return the merged SAML settings (build lazily and cache)."""
    if _SamlConfig.settings_cache is None:
        LOGGER.info("SAML settings cache miss; building settings.")
        _SamlConfig.settings_cache = _build_sp_settings()
    else:
        LOGGER.info("SAML settings cache hit; reusing existing settings.")
    return _SamlConfig.settings_cache


# =============================================================================
# OneLogin plumbing
# =============================================================================
def _starlette_to_saml_request(request: Request) -> Dict[str, Any]:
    """Translate FastAPI/Starlette request to python3-saml expected dict."""
    data = {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.headers.get("host"),
        "script_name": request.scope.get("root_path", ""),
        "server_port": request.url.port
        or (443 if request.url.scheme == "https" else 80),
        "get_data": dict(request.query_params),
        "post_data": {},  # populated for ACS
    }
    LOGGER.info(
        "Converted Starlette request to SAML dict: path=%s, https=%s, host=%s, port=%s",
        request.url.path,
        data["https"],
        data["http_host"],
        data["server_port"],
    )
    return data


def _get_auth(
    request: Request,
    with_post: Optional[dict] = None,
) -> OneLogin_Saml2_Auth:
    """Return a OneLogin_Saml2_Auth instance for the given request."""
    data = _starlette_to_saml_request(request)
    if with_post:
        LOGGER.info(
            "Initializing SAML auth with POST data for path=%s, RelayState=%s",
            request.url.path,
            with_post.get("RelayState"),
        )
        data["post_data"] = with_post
    else:
        LOGGER.info(
            "Initializing SAML auth without POST data for path=%s", request.url.path
        )
    settings = OneLogin_Saml2_Settings(settings=_get_settings_dict())
    return OneLogin_Saml2_Auth(data, old_settings=settings)


# =============================================================================
# Helpers
# =============================================================================
def _path_only(raw: Optional[str]) -> str:
    """Return a safe, path-only string that always starts with '/'."""
    val = raw or "/"
    decoded = urllib.parse.unquote(val)
    cleaned = decoded if decoded.startswith("/") else "/"
    if raw != cleaned:
        LOGGER.info(
            "Normalized path-only value: raw=%r, decoded=%r, cleaned=%r",
            raw,
            decoded,
            cleaned,
        )
    return cleaned


def _extract_identity(auth: OneLogin_Saml2_Auth) -> Dict[str, Any]:
    """Pull identity fields from the SAML assertion."""
    name_id = auth.get_nameid() or ""
    attrs = auth.get_attributes() or {}

    okta_id = (attrs.get("custom:OKTA_ID") or [name_id or ""])[0]
    email = (attrs.get("email") or [None])[0]
    first = (attrs.get("firstName") or attrs.get("given_name") or [""])[0]
    last = (attrs.get("lastName") or attrs.get("family_name") or [""])[0]
    groups = attrs.get("groups") or []

    identity = {
        "okta_id": okta_id,
        "email": email,
        "first": first,
        "last": last,
        "groups": groups,
    }

    LOGGER.info(
        "Extracted SAML identity: okta_id=%s, email=%s, first=%s, last=%s, group_count=%d",
        okta_id,
        email,
        first,
        last,
        len(groups),
    )
    LOGGER.info("SAML identity groups: %s", groups)

    return identity


def _upsert_user(identity: Dict[str, Any]) -> User:
    """Upsert a User keyed by OktaId, with legacy email attachment path."""
    okta_id = identity["okta_id"]
    email = identity["email"]
    first = identity["first"]
    last = identity["last"]
    groups = identity["groups"]

    LOGGER.info(
        "Upserting user from SAML identity: okta_id=%s, email=%s", okta_id, email
    )

    # Try to find the user by OktaId first
    user = User.objects.filter(okta_id=okta_id).first()

    if not user:
        LOGGER.info(
            "No existing user found with okta_id=%s; attempting legacy email lookup for %s",
            okta_id,
            email,
        )
        # If no user with OktaId exists, try to find a legacy user by email
        user = User.objects.filter(email=email).first()
        if user:
            LOGGER.info(
                "Found legacy user with email=%s; attaching okta_id=%s", email, okta_id
            )
            # Update the legacy user in place
            user.okta_id = okta_id
            user.first_name = user.first_name or (first or None)
            user.last_name = user.last_name or (last or None)
        else:
            LOGGER.info(
                "No legacy user for email=%s; creating new user with okta_id=%s",
                email,
                okta_id,
            )
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
        LOGGER.info(
            "Found existing user with okta_id=%s (id=%s); updating identity fields.",
            okta_id,
            user.id,
        )
        # Update the existing user with OktaId
        user.first_name = user.first_name or (first or None)
        user.last_name = user.last_name or (last or None)
        if email and user.email != email:
            LOGGER.info(
                "Updating email for user id=%s from %s to %s",
                user.id,
                user.email,
                email,
            )
            user.email = email

    # Update additional fields
    user.cognito_username = None
    user.cognito_use_case_description = None
    user.cognito_email_verified = True
    user.cognito_groups = groups
    user.last_logged_in = datetime.now(timezone.utc)

    LOGGER.info(
        "Updating login block status for user id=%s (okta_id=%s).",
        getattr(user, "id", None),
        okta_id,
    )
    # Update login block status and save the user
    update_login_block_status(user)
    user.save()
    LOGGER.info("User upserted and saved: id=%s, okta_id=%s", user.id, okta_id)
    return user


def _redirect_with_cookies(relay: Optional[str], token: str) -> RedirectResponse:
    """Return a 303 redirect to the SPA and set auth cookies."""
    relay_path = _path_only(relay)
    target = f"{FRONTEND_DOMAIN.rstrip('/')}{relay_path}"

    LOGGER.info(
        "Redirecting after SAML ACS with RelayState=%r -> relay_path=%r, target=%r",
        relay,
        relay_path,
        target,
    )

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
        samesite="Lax",
        path="/",
    )
    resp.set_cookie(
        "crossfeed-token",
        token,
        secure=is_https,
        samesite="Lax",
        path="/",
    )
    LOGGER.info(
        "Auth cookies set on redirect response; secure=%s, samesite='Lax', path='/'",
        is_https,
    )
    return resp


# =============================================================================
# Routes
# =============================================================================
@router.get("/saml/metadata")
def saml_metadata():
    """Return the SAML SP metadata document."""
    LOGGER.info("Serving SAML SP metadata.")
    settings = OneLogin_Saml2_Settings(settings=_get_settings_dict())
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        LOGGER.error("SP metadata validation failed: %s", errors)
        raise HTTPException(
            status_code=500,
            detail=f"SP metadata invalid: {', '.join(errors)}",
        )
    LOGGER.info("SP metadata validated successfully.")
    return Response(content=metadata, media_type="application/xml")


@router.get("/saml/login")
def saml_login(request: Request, next: str = "/"):
    """
    Start an SP-initiated SAML login.

    Optional `next` controls where the user lands after login.
    """
    raw_next = request.query_params.get("next", next)
    next_path = _path_only(raw_next)
    LOGGER.info(
        "SAML login initiated: path=%s, raw_next=%r, normalized_next=%r",
        request.url.path,
        raw_next,
        next_path,
    )

    auth = _get_auth(request)
    login_url = auth.login(return_to=next_path)
    LOGGER.info("Generated SAML login URL: %s", login_url)
    return RedirectResponse(login_url)


@router.post("/saml/acs")
async def saml_acs(request: Request):
    """Process the SAML response, upsert a user, issue JWT, and set cookies."""
    LOGGER.info("SAML ACS endpoint called for path=%s", request.url.path)
    form = dict(await request.form())
    relay_state = form.get("RelayState")
    LOGGER.info("SAML ACS received RelayState=%r", relay_state)

    auth = _get_auth(request, with_post=form)
    auth.process_response()

    errors = auth.get_errors()
    is_auth = auth.is_authenticated()

    if errors or not is_auth:
        LOGGER.error(
            "SAML auth failed at ACS: errors=%s, is_authenticated=%s",
            errors,
            is_auth,
        )
        raise HTTPException(status_code=401, detail=f"SAML auth failed: {errors}")

    LOGGER.info(
        "SAML auth successful at ACS: is_authenticated=%s",
        is_auth,
    )

    identity = _extract_identity(auth)
    if not identity["okta_id"]:
        LOGGER.error(
            "SAML assertion missing OktaId (NameID/custom:OKTA_ID); identity=%s",
            identity,
        )
        raise HTTPException(
            status_code=400,
            detail="No OktaId (NameID/custom:OKTA_ID) in SAML assertion",
        )

    user = _upsert_user(identity)
    LOGGER.info(
        "Creating JWT token for user id=%s, okta_id=%s", user.id, identity["okta_id"]
    )
    token = create_jwt_token(user)

    LOGGER.info("Validating JSON serialization for user_to_dict output.")
    validate_json_serialization(user_to_dict(user), label="User Dict")

    relay = relay_state or "/"
    LOGGER.info("Final RelayState used for redirect: %r", relay)
    return _redirect_with_cookies(relay, token)


@router.get("/saml/logout")
def saml_logout(request: Request, next: str = "/"):
    """Log the user out of the app and clear auth cookies."""
    raw_next = request.query_params.get("next", next)
    next_path = _path_only(raw_next)
    target = f"{FRONTEND_DOMAIN.rstrip('/')}{next_path}"

    LOGGER.info(
        "SAML logout called: path=%s, raw_next=%r, normalized_next=%r, target=%r",
        request.url.path,
        raw_next,
        next_path,
        target,
    )

    resp = RedirectResponse(target, status_code=303)
    resp.delete_cookie("token", path="/")
    resp.delete_cookie("crossfeed-token", path="/")
    LOGGER.info("Cleared auth cookies on logout response.")
    return resp
