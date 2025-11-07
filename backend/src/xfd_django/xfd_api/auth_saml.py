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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# -----------------------------------------------------------------------------
# Env helpers & config
# -----------------------------------------------------------------------------
def _env_truthy(in_var: Optional[str]) -> bool:
    if in_var is None:
        return False
    return in_var.strip().lower() in {"1", "true", "yes", "y", "on"}


BACKEND_DOMAIN = (os.getenv("BACKEND_DOMAIN") or "").rstrip("/")
FRONTEND_DOMAIN = (os.getenv("FRONTEND_DOMAIN") or "").rstrip("/")
OKTA_METADATA_URL = os.getenv("OKTA_SAML_METADATA_URL")

IS_LOCAL = _env_truthy(os.getenv("IS_LOCAL"))
SAML_SP_CERT_PATH = os.getenv("SAML_SP_CERT_PATH")
SAML_SP_PRIVATE_KEY_PATH = os.getenv("SAML_SP_PRIVATE_KEY_PATH")
WANT_NAMEID_ENCRYPTED = _env_truthy(os.getenv("WANT_NAMEID_ENCRYPTED"))  # optional


def _read_text_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


# -----------------------------------------------------------------------------
# SAML settings
# -----------------------------------------------------------------------------
def _build_sp_settings() -> Dict[str, Any]:
    """Build SAML settings dict by merging SP config with Okta IdP metadata URL."""
    if not OKTA_METADATA_URL:
        raise RuntimeError("OKTA_SAML_METADATA_URL is not set")

    idp_data = OneLogin_Saml2_IdPMetadataParser.parse_remote(OKTA_METADATA_URL)

    sp_settings: Dict[str, Any] = {
        "strict": False,  # flip to True once IdP config is finalized
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
            "wantNameIdEncrypted": False,  # toggled below
            "wantAssertionsEncrypted": False,  # toggled below
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

    if not IS_LOCAL:
        if not SAML_SP_CERT_PATH or not SAML_SP_PRIVATE_KEY_PATH:
            raise RuntimeError(
                "SAML_SP_CERT_PATH and SAML_SP_PRIVATE_KEY_PATH must be set when IS_LOCAL is false."
            )
        sp_cert = _read_text_file(SAML_SP_CERT_PATH)
        sp_key = _read_text_file(SAML_SP_PRIVATE_KEY_PATH)

        sp_settings["sp"]["x509cert"] = sp_cert
        sp_settings["sp"]["privateKey"] = sp_key
        sp_settings["security"]["wantAssertionsEncrypted"] = True
        sp_settings["security"]["wantNameIdEncrypted"] = WANT_NAMEID_ENCRYPTED
        logger.info("SAML assertion encryption ENABLED (non-local environment).")
    else:
        logger.info("SAML assertion encryption DISABLED (local development).")

    settings = OneLogin_Saml2_IdPMetadataParser.merge_settings(sp_settings, idp_data)
    return settings


SAML_SETTINGS_DATA = _build_sp_settings()  # load once at import


# -----------------------------------------------------------------------------
# OneLogin plumbing
# -----------------------------------------------------------------------------
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
    request: Request, with_post: Optional[dict] = None
) -> OneLogin_Saml2_Auth:
    data = _starlette_to_saml_request(request)
    if with_post:
        data["post_data"] = with_post
    settings = OneLogin_Saml2_Settings(settings=SAML_SETTINGS_DATA)
    return OneLogin_Saml2_Auth(data, old_settings=settings)


# -----------------------------------------------------------------------------
# Small helpers to keep endpoint bodies slim (fixes R0915)
# -----------------------------------------------------------------------------
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

    user = User.objects.filter(okta_id=okta_id).first()

    if not user:
        legacy = (
            User.objects.filter(email=email, okta_id__isnull=True).first()
            if email
            else None
        )
        if legacy:
            user = legacy
            user.okta_id = okta_id
            user.first_name = user.first_name or (first or None)
            user.last_name = user.last_name or (last or None)
            if user.invite_pending:
                user.invite_pending = False
        else:
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
        user.first_name = user.first_name or (first or None)
        user.last_name = user.last_name or (last or None)
        if email and user.email != email:
            user.email = email

    # Clean/legacy fields
    user.cognito_username = None
    user.cognito_use_case_description = None
    user.cognito_email_verified = True
    user.cognito_groups = groups
    user.last_logged_in = datetime.now(timezone.utc)

    update_login_block_status(user)
    user.save()
    return user


def _redirect_with_cookies(relay: Optional[str], token: str) -> RedirectResponse:
    """Return a 303 redirect to the SPA and set auth cookies."""
    relay_path = _path_only(relay)
    target = f"{FRONTEND_DOMAIN.rstrip('/')}{relay_path}"
    resp = RedirectResponse(target, status_code=303)

    is_https = BACKEND_DOMAIN.startswith("https://")
    resp.set_cookie(
        "token", token, httponly=False, secure=is_https, samesite="Lax", path="/"
    )
    resp.set_cookie("crossfeed-token", token, secure=is_https, samesite="Lax", path="/")
    return resp


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@router.get("/saml/metadata")
def saml_metadata():
    """SAML SP metadata endpoint."""
    settings = OneLogin_Saml2_Settings(settings=SAML_SETTINGS_DATA)
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    if errors:
        raise HTTPException(
            status_code=500, detail=f"SP metadata invalid: {', '.join(errors)}"
        )
    return Response(content=metadata, media_type="application/xml")


@router.get("/saml/login")
def saml_login(request: Request, next: str = "/"):
    """
    SP-initiated login. Optional `next` controls where the user lands after login.

    Pass a *path-only* RelayState to Okta.
    """
    next_path = _path_only(request.query_params.get("next"))
    auth = _get_auth(request)
    return RedirectResponse(auth.login(return_to=next_path))


@router.post("/saml/acs")
async def saml_acs(request: Request):
    """Process the SAML response posted by Okta.

    Validates th e response, upserts the user, mints a JWT, sets cookies, and
    redirects to the SPA.
    """
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
    # sanity-check JSON shape
    validate_json_serialization(user_to_dict(user), label="User Dict")

    relay = form.get("RelayState") or "/"
    return _redirect_with_cookies(relay, token)


@router.get("/saml/logout")
def saml_logout(request: Request, next: str = "/"):
    """App logout (local). Add SLO later if needed."""
    next_path = _path_only(request.query_params.get("next"))
    target = f"{FRONTEND_DOMAIN.rstrip('/')}{next_path}"
    resp = RedirectResponse(target, status_code=303)
    resp.delete_cookie("token", path="/")
    resp.delete_cookie("crossfeed-token", path="/")
    return resp
