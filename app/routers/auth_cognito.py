import base64, secrets, urllib.parse
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import RedirectResponse
from itsdangerous import TimestampSigner, BadSignature
from starlette import status

from ..auth.cognito_config import (
    CLIENT_ID, CLIENT_SECRET, AUTH_URL, TOKEN_URL, LOGOUT_URL,
    REDIRECT_URI, LOGOUT_REDIRECT_URI
)
from ..auth.cognito_config import STATE_SECRET
from ..auth.cognito_verify import verify_jwt
from ..auth.cognito_config import CLIENT_ID as AUDIENCE

router = APIRouter()

STATE_COOKIE = "oauth_state"
ID_COOKIE = "id_token"
ACCESS_COOKIE = "access_token"
COOKIE_MAX_AGE = 60 * 60  # 1 hour

def set_cookie(resp: Response, key: str, value: str, max_age: int = COOKIE_MAX_AGE):
    resp.set_cookie(
        key,
        value,
        max_age=max_age,
        httponly=True,
        secure=False,  # set True if serving HTTPS
        samesite="lax",
        path="/",
    )

def clear_cookie(resp: Response, key: str):
    resp.delete_cookie(key, path="/")

def _sign_state(raw_state: str) -> str:
    return TimestampSigner(STATE_SECRET).sign(raw_state).decode()

def _unsign_state(signed_state: str, max_age: int = 600) -> str:
    return TimestampSigner(STATE_SECRET).unsign(signed_state, max_age=max_age).decode()

@router.get("/auth/login")
def login(force: bool = False):
    state_raw = secrets.token_urlsafe(24)
    state_signed = _sign_state(state_raw)
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": REDIRECT_URI,
        "state": state_raw,
    }
    if force:
        params["prompt"] = "login"
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    resp = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    set_cookie(resp, STATE_COOKIE, state_signed, max_age=600)
    return resp


@router.get("/auth/callback")
async def callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code/state")

    signed_state = request.cookies.get(STATE_COOKIE)
    if not signed_state:
        raise HTTPException(status_code=400, detail="Missing state cookie")
    try:
        raw_from_cookie = _unsign_state(signed_state, max_age=600)
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid state cookie")
    if raw_from_cookie != state:
        raise HTTPException(status_code=400, detail="State mismatch")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if CLIENT_SECRET:
        basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(TOKEN_URL, data=data, headers=headers)
    if token_resp.status_code != 200:
        raise HTTPException(status_code=token_resp.status_code, detail=f"Token exchange failed: {token_resp.text}")

    tokens = token_resp.json()
    id_token = tokens.get("id_token")
    access_token = tokens.get("access_token")
    if not id_token or not access_token:
        raise HTTPException(status_code=400, detail="Tokens not returned")

    # Verify ID token before setting
    try:
        _ = verify_jwt(id_token, audience=AUDIENCE)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ID token: {e}")

    resp = RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    set_cookie(resp, ID_COOKIE, id_token)
    set_cookie(resp, ACCESS_COOKIE, access_token)
    clear_cookie(resp, STATE_COOKIE)
    return resp

@router.get("/auth/logout")
def logout():
    params = {
        "client_id": CLIENT_ID,
        "logout_uri": LOGOUT_REDIRECT_URI,
    }
    url = f"{LOGOUT_URL}?{urllib.parse.urlencode(params)}"
    resp = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    clear_cookie(resp, ID_COOKIE)
    clear_cookie(resp, ACCESS_COOKIE)
    clear_cookie(resp, STATE_COOKIE)
    return resp

def get_current_user_from_cookie(request: Request):
    token = request.cookies.get(ID_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        claims = verify_jwt(token, audience=AUDIENCE)
        return claims
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token invalid: {e}")

@router.get("/api/me")
def me(claims: dict = Depends(get_current_user_from_cookie)):
    return {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "email_verified": claims.get("email_verified"),
        "name": claims.get("name"),
    }



