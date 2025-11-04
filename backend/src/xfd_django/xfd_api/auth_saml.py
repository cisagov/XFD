"""Auth SAML routes for FastAPI backend."""

# Standard Python Libraries
from datetime import datetime, timezone
import logging
import os
from typing import Optional
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


def _env_truthy(v: Optional[str]) -> bool:
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


APP_BASE_URL = (os.getenv("APP_BASE_URL") or "").rstrip("/")
FRONTEND_BASE_URL = (os.getenv("FRONTEND_BASE_URL") or "").rstrip("/")
OKTA_METADATA_URL = os.getenv("OKTA_SAML_METADATA_URL")

# Conditional encryption controls
IS_LOCAL = _env_truthy(os.getenv("IS_LOCAL"))
SAML_SP_CERT_PATH = os.getenv("SAML_SP_CERT_PATH")
SAML_SP_PRIVATE_KEY_PATH = os.getenv("SAML_SP_PRIVATE_KEY_PATH")
WANT_NAMEID_ENCRYPTED = _env_truthy(os.getenv("WANT_NAMEID_ENCRYPTED"))  # optional


def _read_text_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def _build_sp_settings():
    """Build SAML settings dict by merging our SP config with Okta IdP metadata URL."""
    if not OKTA_METADATA_URL:
        raise RuntimeError("OKTA_SAML_METADATA_URL is not set")

    # Parse IdP metadata (certs, SSO/SLO endpoints)
    idp_data = OneLogin_Saml2_IdPMetadataParser.parse_remote(OKTA_METADATA_URL)

    # === Base SP config (common to all envs) ===
    sp_settings = {
        # keep current; you can switch to True after IdP is finalized
        "strict": False,
        "debug": dj_settings.DEBUG,
        "sp": {
            "entityId": f"{APP_BASE_URL}/saml/metadata",
            "assertionConsumerService": {
                "url": f"{APP_BASE_URL}/saml/acs",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": f"{APP_BASE_URL}/saml/logout",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            # x509cert / privateKey will be injected for non-local envs below
        },
        "security": {
            "authnRequestsSigned": False,
            "logoutRequestSigned": False,
            "logoutResponseSigned": False,
            "wantAssertionsSigned": True,
            "wantMessagesSigned": False,
            "wantNameId": True,
            # These two are toggled based on environment
            "wantNameIdEncrypted": False,
            "wantAssertionsEncrypted": False,
            "requestedAuthnContext": True,
            "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256",
            "relaxDestinationValidation": False,
            "rejectDeprecatedAlgorithm": True,
        },
        "baseurl": f"{APP_BASE_URL}",
        "contactPerson": {},
        "organization": {},
    }

    # === Conditional encryption: only in non-local environments ===
    if not IS_LOCAL:
        # Require paths to cert & private key
        if not SAML_SP_CERT_PATH or not SAML_SP_PRIVATE_KEY_PATH:
            raise RuntimeError(
                "SAML_SP_CERT_PATH and SAML_SP_PRIVATE_KEY_PATH must be set when IS_LOCAL is false."
            )

        sp_cert = _read_text_file(SAML_SP_CERT_PATH)
        sp_key = _read_text_file(SAML_SP_PRIVATE_KEY_PATH)

        # Inject keys so python3-saml can publish the encryption KeyDescriptor in /saml/metadata
        # and decrypt incoming EncryptedAssertions at /saml/acs.
        sp_settings["sp"]["x509cert"] = sp_cert
        sp_settings["sp"]["privateKey"] = sp_key

        # Flip encryption flags ON for non-local
        sp_settings["security"]["wantAssertionsEncrypted"] = True
        sp_settings["security"]["wantNameIdEncrypted"] = WANT_NAMEID_ENCRYPTED

        logger.info("SAML assertion encryption ENABLED (non-local environment).")
    else:
        logger.info("SAML assertion encryption DISABLED (local development).")

    # Merge in IdP info from metadata URL
    settings = OneLogin_Saml2_IdPMetadataParser.merge_settings(sp_settings, idp_data)
    return settings


SAML_SETTINGS_DATA = _build_sp_settings()  # load once at import


def _starlette_to_saml_request(request: Request):
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


@router.get("/saml/metadata")
def saml_metadata():
    """SAML SP metadata endpoint."""
    settings = OneLogin_Saml2_Settings(settings=SAML_SETTINGS_DATA)
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
    SP-initiated login. Optional `next` controls where the user lands after login.

    Pass a *path-only* RelayState to Okta.
    """
    raw_next = request.query_params.get("next") or "/"
    next_decoded = urllib.parse.unquote(raw_next)
    next_path = next_decoded if next_decoded.startswith("/") else "/"

    auth = _get_auth(request)
    return RedirectResponse(auth.login(return_to=next_path))


@router.post("/saml/acs")
async def saml_acs(request: Request):
    """
    Process the SAML response posted by Okta.

    Validate the response, upsert the user keyed by OktaId, mint a JWT, set cookies, and redirect to the SPA.
    """
    form = dict(await request.form())
    auth = _get_auth(request, with_post=form)
    auth.process_response()
    errors = auth.get_errors()

    if errors or not auth.is_authenticated():
        raise HTTPException(status_code=401, detail=f"SAML auth failed: {errors}")

    # --- Identity from assertion ---
    name_id = auth.get_nameid()  # Okta user id (per your config)
    attrs = auth.get_attributes()

    # Prefer explicit custom attribute; fall back to NameID
    okta_id = (attrs.get("custom:OKTA_ID") or [name_id or ""])[0]
    if not okta_id:
        raise HTTPException(
            status_code=400,
            detail="No OktaId (NameID/custom:OKTA_ID) in SAML assertion",
        )

    email = (attrs.get("email") or [None])[0]
    first = (attrs.get("firstName") or attrs.get("given_name") or [""])[0]
    last = (attrs.get("lastName") or attrs.get("family_name") or [""])[0]
    groups = attrs.get("groups") or []

    # --- Upsert by OktaId first ---
    user = User.objects.filter(okta_id=okta_id).first()

    if not user:
        # Attach legacy user by email if present
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

    # Mint internal JWT
    token = create_jwt_token(user)
    payload = {"token": token, "user": user_to_dict(user)}
    validate_json_serialization(payload["user"], label="User Dict")

    # RelayState -> SPA
    relay_raw = form.get("RelayState") or "/"
    relay_decoded = urllib.parse.unquote(relay_raw)
    relay_path = relay_decoded if relay_decoded.startswith("/") else "/"
    target = f"{FRONTEND_BASE_URL.rstrip('/')}{relay_path}"

    # 303 to convert POST->GET
    resp = RedirectResponse(target, status_code=303)

    # Cookies tuned for localhost vs https
    is_https = APP_BASE_URL.startswith("https://")
    resp.set_cookie(
        "token", token, httponly=False, secure=is_https, samesite="Lax", path="/"
    )
    resp.set_cookie("crossfeed-token", token, secure=is_https, samesite="Lax", path="/")
    return resp


@router.get("/saml/logout")
def saml_logout(request: Request, next: str = "/"):
    """App logout (local). Add SLO later if needed."""
    raw_next = request.query_params.get("next") or "/"
    next_decoded = urllib.parse.unquote(raw_next)
    next_path = next_decoded if next_decoded.startswith("/") else "/"

    target = f"{FRONTEND_BASE_URL.rstrip('/')}{next_path}"
    resp = RedirectResponse(target, status_code=303)
    resp.delete_cookie("token", path="/")
    resp.delete_cookie("crossfeed-token", path="/")
    return resp
