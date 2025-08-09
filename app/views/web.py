from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional, Dict, Any

from ..auth.cognito_verify import verify_jwt  # type: ignore
from ..auth.cognito_config import CLIENT_ID as AUDIENCE  # type: ignore

# Dynamo is optional — import safely
try:
    from ..services.dynamo import list_recent_runs, get_usage_today  # type: ignore
except Exception:
    list_recent_runs = None   # type: ignore
    get_usage_today = None    # type: ignore

router = APIRouter()
templates_dir = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

def _get_claims(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get("id_token")
    if not token:
        return None
    try:
        return verify_jwt(token, audience=AUDIENCE)
    except Exception:
        return None

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    claims = _get_claims(request)
    user_email = claims.get("email") if claims else None

    recent_runs = None
    usage = None
    if claims and list_recent_runs and get_usage_today:
        try:
            sub = claims.get("sub")
            recent_runs = list_recent_runs(sub, limit=5)  # type: ignore
            usage = get_usage_today(sub)                  # type: ignore
        except Exception:
            recent_runs, usage = [], {"runs_today": 0}

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Home",
            "user_email": user_email,
            "recent_runs": recent_runs,
            "usage": usage,
        },
    )
