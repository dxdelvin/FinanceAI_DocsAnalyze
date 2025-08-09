import os, time, uuid
from typing import Any, Dict, List, Optional
import boto3
from boto3.dynamodb.conditions import Key

REGION = os.getenv("AWS_REGION", "eu-north-1")
TABLE_NAME = os.getenv("DDB_TABLE")

if not TABLE_NAME:
    raise RuntimeError("DDB_TABLE env is not set")

_dynamo = boto3.resource("dynamodb", region_name=REGION)
_table = _dynamo.Table(TABLE_NAME)

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

def upsert_profile(sub: str, email: str) -> None:
    _table.put_item(Item={
        "PK": f"USER#{sub}",
        "SK": "PROFILE#MAIN",
        "email": email,
        "updated_at": _now_iso(),
    })

def create_run(sub: str, run_type: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    ts = _now_iso()
    item = {
        "PK": f"USER#{sub}",
        "SK": f"RUN#{ts}#{run_id}",
        "run_id": run_id,
        "type": run_type,
        "status": "queued",
        "created_at": ts,
    }
    if payload is not None:
        item["payload"] = payload
    _table.put_item(Item=item)
    return item

def list_recent_runs(sub: str, limit: int = 10) -> List[Dict[str, Any]]:
    resp = _table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{sub}") & Key("SK").begins_with("RUN#"),
        ScanIndexForward=False,
        Limit=limit,
    )
    return resp.get("Items", [])

def list_today_runs(sub: str, limit: int = 20) -> List[Dict[str, Any]]:
    today_prefix = time.strftime("RUN#%Y-%m-%d", time.gmtime())
    resp = _table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{sub}") & Key("SK").begins_with(today_prefix),
        ScanIndexForward=False,
        Limit=limit,
    )
    return resp.get("Items", [])

def bump_rate(sub: str, key: str, ttl_seconds: int = 3600) -> Dict[str, Any]:
    bucket = time.strftime("%Y%m%dT%H", time.gmtime())
    ttl = int(time.time()) + ttl_seconds
    resp = _table.update_item(
        Key={"PK": f"USER#{sub}", "SK": f"RATE#{key}#{bucket}"},
        UpdateExpression="ADD #c :one SET ttl=:ttl",
        ExpressionAttributeNames={"#c": "count"},
        ExpressionAttributeValues={":one": 1, ":ttl": ttl},
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes", {})

def get_usage_today(sub: str) -> Dict[str, Any]:
    items = list_today_runs(sub, limit=100)
    return {"runs_today": len(items)}
