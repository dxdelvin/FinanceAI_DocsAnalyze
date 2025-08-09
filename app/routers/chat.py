from typing import Optional, Any, Dict

from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path

from ..auth.cognito_verify import verify_jwt  # type: ignore
from ..auth.cognito_config import CLIENT_ID as AUDIENCE  # type: ignore

# Social/Dynamo helpers
from ..services.social import (
    create_post, list_feed, toggle_like, repost, upsert_profile,
    search_users_local, list_dm_conversations, send_dm, list_dm
)

# Realtime DM manager (simple in-memory WebSocket hub)
from ..services.realtime import dm_manager  # provides connect(), disconnect(), broadcast()

router = APIRouter(tags=["chat"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)


# ---------- Auth helper ----------
def claims(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("id_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_jwt(token, audience=AUDIENCE)


# ---------- Page: Social Feed ----------
@router.get("/social", response_class=HTMLResponse)
def social_page(request: Request):
    """
    Renders the /social page (social feed).
    """
    email = given = my_sub = None
    try:
        c = claims(request)
        email = c.get("email")
        given = c.get("given_name")
        my_sub = c.get("sub")
        if my_sub:
            upsert_profile(my_sub, email or "", given or "")
    except Exception:
        pass

    return templates.TemplateResponse(
        "social.html",
        {
            "request": request,
            "user_email": email,
            "given_name": given,
            "my_sub": my_sub,
        },
    )


# ---------- Page: People (DMs) ----------
@router.get("/people", response_class=HTMLResponse)
def people_page(request: Request):
    """
    Renders the /people page (DMs only).
    """
    email = given = my_sub = None
    try:
        c = claims(request)
        email = c.get("email")
        given = c.get("given_name")
        my_sub = c.get("sub")
        if my_sub:
            upsert_profile(my_sub, email or "", given or "")
    except Exception:
        pass

    return templates.TemplateResponse(
        "people.html",
        {
            "request": request,
            "user_email": email,
            "given_name": given,
            "my_sub": my_sub,  # used by the client to style own messages
        },
    )


# ---------- Feed APIs (for /social) ----------
class PostIn(BaseModel):
    text: str


class LikeIn(BaseModel):
    post_id: str


class RepostIn(BaseModel):
    post_id: str


@router.post("/api/social/post")
def api_post(data: PostIn, request: Request):
    c = claims(request)
    txt = (data.text or "").strip()
    if not txt:
        raise HTTPException(status_code=400, detail="Text required")
    item = create_post(
        c["sub"], c.get("given_name") or c.get("email") or "anon", txt
    )
    return {"post": item}


@router.get("/api/social/feed")
def api_feed(limit: int = 20, cursor: Optional[str] = None):
    return list_feed(limit=limit, cursor=cursor)


@router.post("/api/social/like")
def api_like(data: LikeIn, request: Request):
    c = claims(request)
    return toggle_like(data.post_id, c["sub"])


@router.post("/api/social/repost")
def api_repost(data: RepostIn, request: Request):
    c = claims(request)
    return repost(data.post_id, c["sub"])


# ---------- Users / Connections ----------
@router.get("/api/chat/users")
def api_users(q: str, limit: int = 8):
    return {"items": search_users_local(q, limit=limit)}


@router.get("/api/chat/connections")
def api_connections(request: Request):
    c = claims(request)
    return {"conversations": list_dm_conversations(c["sub"])}


@router.post("/api/chat/connect")
def api_connect(target_sub: str, request: Request):
    # For simplicity, connection creation lives in services.social.connect_users
    from ..services.social import connect_users  # lazy import to avoid cycle
    c = claims(request)
    return connect_users(c["sub"], target_sub)


# ---------- Direct Messages ----------
class DMIn(BaseModel):
    to_sub: str
    text: str


@router.post("/api/chat/dm")
async def api_dm(data: DMIn, request: Request):
    """
    Create a DM (persists to DynamoDB) and push it to both participants via WebSocket.
    """
    c = claims(request)
    res = send_dm(c["sub"], data.to_sub, data.text)
    # Broadcast in real-time to the conversation room
    await dm_manager.broadcast(c["sub"], data.to_sub, {"type": "dm", "item": res["msg"]})
    return res


@router.get("/api/chat/dm")
def api_dm_list(with_sub: str, request: Request, limit: int = 50):
    c = claims(request)
    return {"items": list_dm(c["sub"], with_sub, limit=limit)}


# ---------- WebSocket for realtime DMs ----------
@router.websocket("/ws/dm/{peer_sub}")
async def ws_dm(websocket: WebSocket, peer_sub: str):
    """
    WebSocket endpoint that joins a DM room (me <-> peer_sub) and receives
    push updates when either participant sends a message.
    """
    # Authenticate from cookie
    token = websocket.cookies.get("id_token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        c = verify_jwt(token, audience=AUDIENCE)
    except Exception:
        await websocket.close(code=4403)
        return

    me = c["sub"]
    await dm_manager.connect(websocket, me, peer_sub)

    try:
        # We don't accept client->server messages over WS (HTTP POST handles sends).
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        dm_manager.disconnect(websocket, me, peer_sub)