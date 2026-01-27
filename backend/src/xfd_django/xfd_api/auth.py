"""Authentication utilities for the FastAPI application."""

# Standard Python Libraries
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import logging
import os
import re
import secrets
from typing import Optional
import urllib.parse
from urllib.parse import urlencode
import uuid

# Third-Party Libraries
from django.conf import settings
from django.forms.models import model_to_dict
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyHeader
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import jwt
import requests
from xfd_api.helpers.email import ensure_zscaler_cert_downloaded
from xfd_mini_dl.models import (
    ApiKey,
    Notification,
    Organization,
    OrganizationTag,
    Role,
    User,
)

JWT_SECRET = settings.JWT_SECRET
SECRET_KEY = settings.SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_TIMEOUT_HOURS = settings.JWT_TIMEOUT_HOURS
OAUTH_META_SECRET = os.getenv("CSRF_SECRET", "super-secret")

AUTH_COOKIE_NAME = "crossfeed-token"  # Choosing this over legacy "token"
LEGACY_AUTH_COOKIE_NAME = "token"  # Optional: legacy support during rollout
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"
# Endpoints that MUST NOT require CSRF, because they establish sessions/cookies
CSRF_EXEMPT_PATH_PREFIXES = (
    "/auth/",  # okta callback, oauth meta, etc.
    "/saml/",  # saml login/acs/logout/metadata
    "/healthcheck",
)

LOGGER = logging.getLogger(__name__)

# User Types excluded from maintenance login blockers.
LOGIN_BLOCKED_EXCLUSIONS = ["globalAdmin", "regionalAdmin"]

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)
serializer = URLSafeTimedSerializer(OAUTH_META_SECRET)
IS_DMZ = os.getenv("IS_DMZ", "0") == "1"


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
IS_LOCAL = _env_truthy(os.getenv("IS_LOCAL"))
COOKIE_DOMAIN = determine_cookie_domain(FRONTEND_DOMAIN, IS_LOCAL)
CSRF_HEADER_NAME = "X-CSRF-Token"
AUTH_COOKIE_NAMES = ("crossfeed-token", "token")  # confirm and cleanup later
CSRF_COOKIE_CANDIDATES = ("csrf", "xsrf", "csrf-token", "xsrf-token")


def _has_auth_header(request: Request) -> bool:
    # Authorization: Bearer <token> OR raw token
    auth = request.headers.get("Authorization") or ""
    if auth.strip():
        return True

    # API key header
    api_key = request.headers.get("X-API-KEY") or ""
    if api_key.strip():
        return True

    return False


def _get_auth_cookie(request: Request) -> str | None:
    """Get auth cookie value from request, if present."""
    for name in AUTH_COOKIE_NAMES:
        val = request.cookies.get(name)
        if val:
            return val
    return None


def _get_csrf_cookie(request: Request) -> str | None:
    """Get CSRF cookie value from request, if present."""
    # If you have a single known cookie name, just use it directly.
    for k, v in request.cookies.items():
        lk = k.lower()
        if any(tok in lk for tok in CSRF_COOKIE_CANDIDATES):
            return v
    return None


async def csrf_protect(request: Request) -> None:
    """Double-submit CSRF protection."""
    # Allow safe methods / preflight
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Allow auth/bootstrap endpoints to set cookies without CSRF
    path = request.url.path or "/"
    if any(path.startswith(pfx) for pfx in CSRF_EXEMPT_PATH_PREFIXES):
        return

    # ✅ If the request is using header-based auth, CSRF is not relevant.
    # This prevents "sticky cookie" failures in tests and avoids forcing CSRF on API clients.
    if _has_auth_header(request):
        return

    # Only enforce CSRF if the request is using cookie auth.
    # If there's no auth cookie, don't block here — let auth dependencies return 401 where appropriate.
    if not _get_auth_cookie(request):
        return

    csrf_cookie = _get_csrf_cookie(request)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
    # """Double-submit CSRF protection."""
    # # Allow safe methods / preflight
    # if request.method in ("GET", "HEAD", "OPTIONS"):
    #     return

    # # Allow auth/bootstrap endpoints to set cookies without CSRF
    # path = request.url.path or "/"
    # if any(path.startswith(pfx) for pfx in CSRF_EXEMPT_PATH_PREFIXES):
    #     return

    # # Only enforce CSRF if the request is using cookie auth.
    # # If there's no auth cookie, don't block here — let auth dependencies return 401 where appropriate.
    # if not _get_auth_cookie(request):
    #     return

    # csrf_cookie = _get_csrf_cookie(request)
    # csrf_header = request.headers.get(CSRF_HEADER_NAME)

    # if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="CSRF validation failed",
    #     )


# V2 test version of csrf_protect using async def
# async def csrf_protect(request: Request) -> None:
#     # Only enforce CSRF for state-changing requests
#     if request.method in ("GET", "HEAD", "OPTIONS"):
#         return

#     # If there's no auth cookie, treat as unauthenticated (401),
#     # not a CSRF failure (403).
#     if not _get_auth_cookie(request):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="No valid authentication credentials provided",
#         )

#     csrf_cookie = _get_csrf_cookie(request)
#     csrf_header = request.headers.get(CSRF_HEADER_NAME)

#     if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="CSRF validation failed",
#         )


# def csrf_protect(request: Request) -> None:
#     """
#     Double-submit CSRF protection.

#     - For unsafe methods, require:
#         cookie csrf_token == header x-csrf-token
#     - Skip GET/HEAD/OPTIONS
#     - Skip exempt paths (auth bootstrap)
#     """
#     # Always allow safe methods / preflight
#     if request.method in ("GET", "HEAD", "OPTIONS"):
#         return

#     path = request.url.path or "/"
#     if any(path.startswith(pfx) for pfx in CSRF_EXEMPT_PATH_PREFIXES):
#         return

#     cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
#     header_token = request.headers.get(CSRF_HEADER_NAME)

#     if not cookie_token or not header_token or cookie_token != header_token:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="CSRF validation failed",
#         )


def _cookie_domain_from_frontend(frontend_domain: str, is_local: bool) -> Optional[str]:
    """Determine the correct cookie domain based on the frontend domain."""
    # reuse your logic if you want; simplest safe default:
    return None if is_local else None


def check_is_https(request: Request) -> bool:
    """Determine if the current request is HTTPS."""
    # Prefer proxy header
    xf_proto = request.headers.get("x-forwarded-proto")
    if xf_proto:
        return xf_proto.lower() == "https"

    # Fallback (local dev, no proxy)
    return request.url.scheme == "https"


def set_auth_and_csrf_cookies(
    response,
    token: str,
    request: Request,
) -> None:
    """Set authentication and CSRF cookies in the response."""
    secure = check_is_https(request)
    samesite = "None" if secure and not IS_LOCAL else "Lax"

    # --- auth cookie (HttpOnly) ---
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
        domain=COOKIE_DOMAIN,
    )

    # --- csrf cookie (readable by JS) ---
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=secure,
        samesite=samesite,
        path="/",
        domain=COOKIE_DOMAIN,
    )


def clear_auth_and_csrf_cookies(resp: Response, request: Request) -> None:
    """Clear authentication and CSRF cookies in the response."""
    common = {
        "path": "/",
        "domain": COOKIE_DOMAIN,
    }

    # Auth cookies
    resp.delete_cookie(AUTH_COOKIE_NAME, **common)

    # CSRF cookies (whatever names you used)
    resp.delete_cookie(CSRF_COOKIE_NAME, **common)


def validate_json_serialization(user_object, label="user_object"):
    """Try to serialize an object to JSON. If it fails, identify which field caused it."""
    if user_object is None:
        raise ValueError("{} is None, cannot serialize".format(label))
    try:
        json.dumps(user_object)
    except TypeError as e:

        def traverse_data(user_data, path):
            if isinstance(user_data, dict):
                for key, value in user_data.items():
                    traverse_data(value, path + [str(key)])
            elif isinstance(user_data, list):
                for index, item in enumerate(user_data):
                    traverse_data(item, path + ["[{}]".format(index)])
            else:
                try:
                    json.dumps(user_data)
                except TypeError:
                    path_str = ".".join(path)
                    raise TypeError(
                        "{} contains unserializable value at `{}`".format(
                            label, path_str
                        )
                    )

        traverse_data(user_object, [])
        raise TypeError("{} failed JSON serialization: {}".format(label, e))


def user_to_dict(user):
    """Take a user model object from django and sanitize fields for output."""
    user_dict = model_to_dict(user)
    # Convert any UUID fields to strings
    for key, val in user_dict.items():
        if isinstance(val, uuid.UUID):
            user_dict[key] = str(val)
        elif isinstance(val, datetime):
            user_dict[key] = str(val)
    # Make sure maintenance checks are included in user response
    user_dict["login_blocked_by_maintenance"] = user.login_blocked_by_maintenance
    return user_dict


def create_jwt_token(user):
    """Create a JWT token for a given user."""
    payload = {
        "id": str(user.id),
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=int(JWT_TIMEOUT_HOURS)),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_token_from_header(request: Request) -> Optional[str]:
    """Extract token from the Authorization header, allowing 'Bearer' or raw tokens."""
    auth_header = request.headers.get("Authorization")
    if auth_header:
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        return auth_header  # Return the token directly if no 'Bearer ' prefix
    for name in ("token", "crossfeed-token"):
        request_token = request.cookies.get(name)
        if request_token and request_token not in ("null", "undefined", "None", ""):
            return request_token
    return None


def get_user_by_api_key(api_key: str):
    """Get a user by their API key."""
    hashed_key = sha256(api_key.encode()).hexdigest()
    try:
        api_key_instance = ApiKey.objects.get(hashed_key=hashed_key)
        api_key_instance.lastUsed = datetime.now(timezone.utc)
        api_key_instance.save(update_fields=["last_used"])
        return api_key_instance.user
    except ApiKey.DoesNotExist:
        LOGGER.warning("API Key not found")
        return None


# Endpoint Authorization Function
def get_current_active_user(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(get_token_from_header),
):
    """Ensure the current user is authenticated and active, supporting either API key or token."""
    user = None
    if api_key:
        user = get_user_by_api_key(api_key)
    elif token:
        # Check if token is an API key
        if re.match(r"^[A-Fa-f0-9]{32}$", token):
            user = get_user_by_api_key(token)
        else:
            try:
                # Decode token in Authorization header to get user
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("id")

                if user_id is None:
                    LOGGER.warning("No user ID found in token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                # Fetch the user by ID from the database
                user = User.objects.get(id=user_id)
            except jwt.ExpiredSignatureError:
                LOGGER.warning("Token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.InvalidTokenError:
                LOGGER.warning("Invalid token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication credentials provided",
        )

    if user is None:
        LOGGER.warning("User not authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    if user.invite_pending:
        LOGGER.warning("User is not active or approved")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized",
        )

    # Attach email to request state for logging
    request.state.user_email = user.email
    return user


def get_current_active_user_unsafe(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    token: Optional[str] = Depends(get_token_from_header),
):
    """
    Ensure the current user is authenticated and active, does not perform invite_pending check.

    This function is UNSAFE and should not be used for sensitive operations.

    It is intended for scenarios where the user is known to be unapproved and where the endpoints are not sensitive.
    """
    user = None
    if api_key:
        user = get_user_by_api_key(api_key)
    elif token:
        # Check if token is an API key
        if re.match(r"^[A-Fa-f0-9]{32}$", token):
            user = get_user_by_api_key(token)
        else:
            try:
                # Decode token in Authorization header to get user
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = payload.get("id")

                if user_id is None:
                    LOGGER.warning("No user ID found in token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                # Fetch the user by ID from the database
                user = User.objects.get(id=user_id)
            except jwt.ExpiredSignatureError:
                LOGGER.warning("Token has expired")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            except jwt.InvalidTokenError:
                LOGGER.warning("Invalid token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication credentials provided",
        )

    if user is None:
        LOGGER.warning("User not authenticated")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # Attach email to request state for logging
    request.state.user_email = user.email
    return user


def update_login_block_status(user: User) -> None:
    """Set user's login_blocked_by_maintenance based on active maintenance window."""
    # Get current time (UTC) TODO: Check notifications TZ and confirm UTC on save.
    now = datetime.now(timezone.utc)

    # Check for active notifications using current time.
    active_maintenance = Notification.objects.filter(
        start_datetime__lte=now,
        end_datetime__gte=now,
        maintenance_type="major",
        status="active",
        # message="waiting_room"  # uncomment if filtering by message later
    ).exists()

    # Only block users who are NOT in LOGIN_BLOCKED_EXCLUSIONS
    user.login_blocked_by_maintenance = (
        active_maintenance and user.user_type not in LOGIN_BLOCKED_EXCLUSIONS
    )
    user.save()


def sign_oauth_data(state: str, code_verifier: str) -> str:
    """Sign oath data."""
    return serializer.dumps(
        {"state": state, "code_verifier": code_verifier}, salt="oauth"
    )


def verify_oauth_data(token: str, max_age: int = 300):
    """Verify oauth data."""
    try:
        return serializer.loads(token, salt="oauth", max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


# POST: /auth/okta-callback
async def handle_okta_callback(request):
    """POST API LOGIC."""
    body = await request.json()
    code = body.get("code")
    state = body.get("state")
    signed_token = body.get("signedToken")

    if not code or not state or not signed_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required OAuth parameters",
        )

    # Validate signed token
    token_data = verify_oauth_data(signed_token)
    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if token_data["state"] != state:
        raise HTTPException(status_code=400, detail="State mismatch")

    code_verifier = token_data["code_verifier"]

    jwt_data = await get_jwt_from_code(code, code_verifier)
    if jwt_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization code or failed to retrieve tokens",
        )

    decoded_token = jwt_data.get("decoded_token")
    resp = await process_user(decoded_token)
    token = resp.get("token")

    # Prepare final response
    response = JSONResponse(content={"message": "User authenticated", "data": resp})

    set_auth_and_csrf_cookies(response, token, request)

    # Optional: keep legacy cookie names during migration
    return response


async def process_user(decoded_token):
    """Process a user based on decoded token information."""
    okta_id = decoded_token["sub"]
    email = decoded_token["email"]

    user = User.objects.filter(okta_id=okta_id).first()

    if not user:
        # Look for legacy user by email with null okta_id
        user = User.objects.filter(email=email, okta_id__isnull=True).first()

        if user:
            # Assign new okta_id to legacy user
            user.okta_id = okta_id
            user.first_name = user.first_name or decoded_token.get("given_name")
            user.last_name = user.last_name or decoded_token.get("family_name")
            user.invite_pending = False
        else:
            # Create new user if no match found
            user = User(
                email=email,
                okta_id=okta_id,
                first_name=decoded_token.get("given_name"),
                last_name=decoded_token.get("family_name"),
                user_type="standard",
                invite_pending=True,
                can_select_own_state=True,
            )

    # Update common fields
    user.last_logged_in = datetime.now()
    user.last_notified_30 = None
    user.cognito_username = decoded_token.get("cognito:username")
    user.cognito_use_case_description = decoded_token.get("nickname")
    user.cognito_email_verified = decoded_token.get("email_verified")
    user.cognito_groups = decoded_token.get("cognito:groups")

    update_login_block_status(user)
    user.save()

    if user:
        # TODO: Uncomment if we want to fully block logins during maintenance windows.
        # Safeguard for preventing logins by returning 403 if login_blocked_by_maintenance.
        # if user.login_blocked_by_maintenance:
        #     raise HTTPException(
        #         status_code=403, detail="Login is currently blocked due to maintenance."
        #     )
        if not JWT_SECRET:
            LOGGER.error("JWT_SECRET is not defined in settings.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # Generate JWT token
        signed_token = jwt.encode(
            {
                "id": str(user.id),
                "email": user.email,
                "exp": datetime.utcnow() + timedelta(hours=int(JWT_TIMEOUT_HOURS)),
            },
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )

        process_resp = {"token": signed_token, "user": user_to_dict(user)}
        validate_json_serialization(process_resp["user"], label="User Dict")
        return process_resp
    else:
        raise HTTPException(status_code=400, detail="User not found")


async def get_jwt_from_code(auth_code: str, code_verifier: str):
    """Exchange authorization code for JWT tokens and decode."""
    try:
        callback_url = os.getenv("VITE_COGNITO_CALLBACK_URL")
        client_id = os.getenv("VITE_COGNITO_CLIENT_ID")
        domain = os.getenv("VITE_COGNITO_DOMAIN")

        authorize_token_url = "https://{}/oauth2/token".format(domain)
        authorize_token_body = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": auth_code,
            "redirect_uri": callback_url,
            "code_verifier": code_verifier,
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        if IS_DMZ:
            response = requests.post(
                authorize_token_url,
                headers=headers,
                data=urlencode(authorize_token_body),
                timeout=20,  # Timeout in seconds
            )
        else:
            zscaler_cert_path = ensure_zscaler_cert_downloaded()
            response = requests.post(
                authorize_token_url,
                headers=headers,
                data=urlencode(authorize_token_body),
                timeout=20,  # Timeout in seconds
                verify=zscaler_cert_path,
            )
        token_response = response.json()
        # Convert the id_token to bytes
        id_token = token_response["id_token"].encode("utf-8")
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")

        # Decode the token without verifying the signature (if needed)
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        LOGGER.info("decoded token: %s", decoded_token)
        return {
            "refresh_token": refresh_token,
            "id_token": id_token,
            "access_token": access_token,
            "decoded_token": decoded_token,
        }

    except Exception as error:
        LOGGER.error("get_jwt_from_code post error: %s", error)


def is_global_write_admin(current_user) -> bool:
    """Check if the user has global write admin permissions."""
    return current_user and current_user.user_type == "globalAdmin"


def is_global_view_admin(current_user) -> bool:
    """Check if the user has global view permissions."""
    return current_user and current_user.user_type in ["globalView", "globalAdmin"]


def is_regional_admin(current_user) -> bool:
    """Check if the user has regional admin permissions."""
    return current_user and current_user.user_type in ["regionalAdmin", "globalAdmin"]


def is_org_admin(current_user, organization_id) -> bool:
    """Check if the user is an admin of the given organization."""
    if not organization_id:
        return False

    # Check if the user has an admin role in the given organization
    for role in current_user.roles.all():
        if str(role.organization.id) == str(organization_id) and role.role == "admin":
            return True

    # If the user is a global write admin, they are considered an org admin
    return is_global_write_admin(current_user)


def is_regional_admin_for_organization(current_user, organization_id) -> bool:
    """Check if user is a regional admin and if a selected organization belongs to their region."""
    if not organization_id:
        return False

    # Check if the user is a regional admin
    if is_regional_admin(current_user):
        # Check if the organization belongs to the user's region
        user_region_id = (
            current_user.region_id
        )  # Assuming this is available in the user object
        organization_region_id = get_organization_region(
            organization_id
        )  # Function to fetch the organization's region
        return user_region_id == organization_region_id

    return False


def can_access_user(current_user, target_user_id) -> bool:
    """Check if current user is allowed to modify.the target user."""
    if not target_user_id:
        return False

    # Check if the current user is the target user or a global write admin
    if (
        str(current_user.id) == str(target_user_id)
        or is_global_write_admin(current_user)
        or is_regional_admin(current_user)
    ):
        return True

    return False


def get_allowed_user_update_fields(current_user, target_user):
    """Get allowed user update fields."""
    if is_global_write_admin(current_user):
        return {
            "first_name",
            "last_name",
            "state",
            "region_id",
            "user_type",
            "invite_pending",
            "date_approved",
            "approved_by",
            "accepted_terms_version",
            "login_blocked_by_maintenance",
            "first_login",
        }

    if is_regional_admin(current_user):
        return {
            "first_name",
            "last_name",
            "state",
            "region_id",
            "invite_pending",
            "first_login",
            "date_approved",
            "approved_by",
        }

    # Self-updates:
    if current_user.id == target_user.id:
        allowed = {"first_login"}  # allow the user to dismiss their own first_login
        if (
            current_user.can_select_own_state is True
            and current_user.invite_pending is True
        ):
            allowed |= {"can_select_own_state", "state", "region_id", "invite_pending"}
        return allowed

    return set()


def get_org_memberships(current_user) -> list[str]:
    """Return the organization IDs that a user is a member of."""
    # Check if the user has a 'roles' attribute and it's not None

    roles = Role.objects.filter(user=current_user)
    return [role.organization.id for role in roles if role.organization]


def get_organization_region(organization_id: str) -> str:
    """Fetch the region ID for the given organization."""
    organization = Organization.objects.get(id=organization_id)
    return organization.region_id


def get_tag_organizations(current_user, tag_id) -> list[str]:
    """Return the organizations belonging to a tag, if the user can access the tag."""
    # Check if the user is a global view admin
    if not is_global_view_admin(current_user):
        return []

    # Fetch the OrganizationTag and its related organizations
    tag = (
        OrganizationTag.objects.prefetch_related("organizations")
        .filter(id=tag_id)
        .first()
    )
    if tag:
        # Return a list of organization IDs
        return [org.id for org in tag.organizations.all()]

    # Return an empty list if tag is not found
    return []


def matches_user_region(current_user, user_region_id: str) -> bool:
    """Check if the current user's region matches the user's region being modified."""
    # Check if the current user is a global admin (can match any region)
    if is_global_write_admin(current_user):
        return True

    # Ensure the user has a region associated with them
    if not current_user.region_id or not user_region_id:
        return False

    # Compare the region IDs
    return user_region_id == current_user.region_id


def get_stats_org_ids(current_user, filters):
    """Get organization ids that a user has access to for the stats."""
    # Extract filters from the Pydantic model
    regions_filter = filters.filters.regions if filters and filters.filters else []
    organizations_filter = (
        filters.filters.organizations if filters and filters.filters else []
    )
    if organizations_filter == [""]:
        organizations_filter = []
    tags_filter = filters.filters.tags if filters and filters.filters else []

    # Final list of organization IDs
    organization_ids = set()

    # Case 1: Explicit organization IDs in filters
    if organizations_filter:
        # Check user type restrictions for provided organization IDs
        for org_id in organizations_filter:
            if (
                is_global_view_admin(current_user)
                or (is_regional_admin_for_organization(current_user, org_id))
                or (is_org_admin(current_user, org_id))
                or (get_org_memberships(current_user))
            ):
                organization_ids.add(org_id)

        if not organization_ids:
            raise HTTPException(
                status_code=403,
                detail="User does not have access to the specified organizations.",
            )

    # Case 2: Global view admin (if no explicit organization filter)
    elif is_global_view_admin(current_user):
        # Get organizations by region
        if regions_filter:
            organizations_by_region = Organization.objects.filter(
                region_id__in=regions_filter
            ).values_list("id", flat=True)
            organization_ids.update(organizations_by_region)

        # Get organizations by tag
        for tag_id in tags_filter:
            organizations_by_tag = get_tag_organizations(current_user, tag_id)
            organization_ids.update(organizations_by_tag)

    # Case 3: Regional admin
    elif current_user.user_type in ["regionalAdmin"]:
        user_region_id = current_user.region_id

        # Allow only organizations in the user's region
        organizations_in_region = Organization.objects.filter(
            region_id=user_region_id
        ).values_list("id", flat=True)
        organization_ids.update(organizations_in_region)

        # Apply filters within the user's region
        if regions_filter and user_region_id in regions_filter:
            organization_ids.update(organizations_in_region)

        # Include organizations by tag within the same region
        for tag_id in tags_filter:
            tag_organizations = get_tag_organizations(current_user, tag_id)
            regional_tag_organizations = [
                org_id
                for org_id in tag_organizations
                if get_organization_region(org_id) == user_region_id
            ]
            organization_ids.update(regional_tag_organizations)

    # Case 4: Standard user
    else:
        # Allow only organizations where the user is a member
        user_organization_ids = current_user.roles.values_list(
            "organization_id", flat=True
        )
        organization_ids.update(user_organization_ids)

    return organization_ids
