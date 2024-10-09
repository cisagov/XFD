"""Auth API logic"""
# Standard Python Libraries
import json

# Third-Party Libraries
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from xfd_api.auth import get_jwt_from_code, process_user


async def handle_okta_callback(request):
    """POST API LOGIC"""
    print(f"Request from /auth/okta-callback: {str(request)}")
    body = await request.json()
    print(f"Request json from callback: {str(request)}")
    print(f"Request json from callback: {body}")
    print(f"Body type: {type(body)}")
    code = body.get("code")
    print(f"Code: {code}")
    if not code:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code not found in request body",
        )
    jwt_data = await get_jwt_from_code(code)
    print(f"JWT Data: {jwt_data}")
    if jwt_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authorization code or failed to retrieve tokens",
        )
    access_token = jwt_data.get("access_token")
    refresh_token = jwt_data.get("refresh_token")
    decoded_token = jwt_data.get("decoded_token")

    resp = await process_user(decoded_token, access_token, refresh_token)
    token = resp.get("token")

    # Create a JSONResponse object to return the response and set the cookie
    response = JSONResponse(
        content={"message": "User authenticated", "data": resp, "token": token}
    )
    response.body = resp
    # response.body = resp
    response.set_cookie(key="token", value=token)

    # Set the 'crossfeed-token' cookie
    response.set_cookie(
        key="crossfeed-token",
        value=token,
        # httponly=True,  # This makes the cookie inaccessible to JavaScript
        # secure=True,    # Ensures the cookie is only sent over HTTPS
        # samesite="Lax"  # Restricts when cookies are sent, adjust as necessary (e.g., "Strict" or "None")
    )
    return response
