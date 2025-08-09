from typing import Optional, Any, Dict
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from ..auth.cognito_verify import verify_jwt  # type: ignore
from ..auth.cognito_config import CLIENT_ID as AUDIENCE  # type: ignore

try:
    from ..services.dynamo import create_run, list_recent_runs, get_usage_today
except Exception as e:
    create_run = list_recent_runs = get_usage_today = None  # type: ignore
    _ddb_import_err = e
else:
    _ddb_import_err = None

router = APIRouter(prefix="/api", tags=["runs"])

def _claims(request: Request) -> Dict[str, Any]:
    token = request.cookies.get("id_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_jwt(token, audience=AUDIENCE)

class RunIn(BaseModel):
    type: str
    payload: Optional[Dict[str, Any]] = None

@router.post("/runs")
def api_create_run(data: RunIn, request: Request):
    if _ddb_import_err or create_run is None:
        raise HTTPException(status_code=503, detail=f"Dynamo not configured: {_ddb_import_err}")
    sub = _claims(request).get("sub")
    item = create_run(sub, data.type, data.payload or {})
    return {"ok": True, "run": item}

@router.get("/runs")
def api_list_runs(request: Request, limit: int = 10):
    if _ddb_import_err or list_recent_runs is None:
        raise HTTPException(status_code=503, detail=f"Dynamo not configured: {_ddb_import_err}")
    sub = _claims(request).get("sub")
    items = list_recent_runs(sub, limit=limit)
    return {"items": items}

@router.get("/usage-today")
def api_usage_today(request: Request):
    if _ddb_import_err or get_usage_today is None:
        raise HTTPException(status_code=503, detail=f"Dynamo not configured: {_ddb_import_err}")
    sub = _claims(request).get("sub")
    usage = get_usage_today(sub)
    return usage
