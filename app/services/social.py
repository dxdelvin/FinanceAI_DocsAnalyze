import os, time, uuid
from typing import Any, Dict, List, Optional
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

REGION = os.getenv("AWS_REGION", "eu-north-1")
TABLE_NAME = os.getenv("DDB_TABLE")
if not TABLE_NAME:
    raise RuntimeError("DDB_TABLE env is not set")

dynamo = boto3.resource("dynamodb", region_name=REGION)
table = dynamo.Table(TABLE_NAME)

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

# ---------- FEED POSTS ----------

def create_post(author_sub: str, author_name: str, text: str) -> Dict[str, Any]:
    post_id = str(uuid.uuid4())
    ts = _now_iso()
    feed_pk = "APP#FEED"
    feed_sk = f"POST#{ts}#{post_id}"
    item = {
        "PK": feed_pk, "SK": feed_sk,
        "post_id": post_id,
        "author_sub": author_sub,
        "author_name": author_name,
        "text": text[:1000],
        "like_count": 0,
        "repost_count": 0,
        "created_at": ts,
        "type": "post"
    }
    table.put_item(Item=item)
    # pointer under user (optional)
    table.put_item(Item={
        "PK": f"USER#{author_sub}", "SK": f"POST#{ts}#{post_id}",
        "ref_pk": feed_pk, "ref_sk": feed_sk, "type": "user_post"
    })
    # mapping for convenience
    table.put_item(Item={
        "PK": f"POST#{post_id}", "SK": "MAP#FEED", "feed_pk": feed_pk, "feed_sk": feed_sk
    })
    return item

def list_feed(limit: int = 20, cursor: Optional[str] = None) -> Dict[str, Any]:
    kwargs = {
        "KeyConditionExpression": Key("PK").eq("APP#FEED") & Key("SK").begins_with("POST#"),
        "ScanIndexForward": False, "Limit": limit
    }
    if cursor:
        try:
            pk, sk = cursor.split("|", 1)
            kwargs["ExclusiveStartKey"] = {"PK": pk, "SK": sk}
        except Exception:
            pass
    resp = table.query(**kwargs)
    items = resp.get("Items", [])
    next_cursor = None
    if "LastEvaluatedKey" in resp:
        lek = resp["LastEvaluatedKey"]
        next_cursor = f"{lek['PK']}|{lek['SK']}"
    return {"items": items, "next": next_cursor}

def _get_feed_key_from_post(post_id: str) -> Optional[Dict[str, str]]:
    resp = table.get_item(Key={"PK": f"POST#{post_id}", "SK": "MAP#FEED"})
    m = resp.get("Item")
    if not m: return None
    return {"PK": m["feed_pk"], "SK": m["feed_sk"]}

def toggle_like(post_id: str, user_sub: str) -> Dict[str, Any]:
    like_key = {"PK": f"POST#{post_id}", "SK": f"LIKE#{user_sub}"}
    try:
        table.put_item(Item={**like_key, "ts": _now_iso()}, ConditionExpression="attribute_not_exists(PK)")
        liked = True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            table.delete_item(Key=like_key)
            liked = False
        else:
            raise
    feed_key = _get_feed_key_from_post(post_id)
    if feed_key:
        table.update_item(
            Key=feed_key,
            UpdateExpression="ADD like_count :d",
            ExpressionAttributeValues={":d": 1 if liked else -1},
            ReturnValues="UPDATED_NEW"
        )
    return {"liked": liked}

def repost(post_id: str, user_sub: str) -> Dict[str, Any]:
    feed_key = _get_feed_key_from_post(post_id)
    if feed_key:
        table.update_item(
            Key=feed_key,
            UpdateExpression="ADD repost_count :one",
            ExpressionAttributeValues={":one": 1},
            ReturnValues="UPDATED_NEW"
        )
    table.put_item(Item={
        "PK": f"USER#{user_sub}", "SK": f"REPOST#{post_id}#{_now_iso()}", "type":"repost"
    })
    return {"ok": True}

# ---------- USERS ----------

def upsert_profile(sub: str, email: str, given_name: Optional[str] = None):
    table.put_item(Item={
        "PK": f"USER#{sub}",
        "SK": "PROFILE#MAIN",
        "email": email,
        "given_name": given_name or "",
        "updated_at": _now_iso(),
        "type":"profile"
    })

def search_users_local(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    q = query.lower()
    resp = table.scan(
        FilterExpression=Attr("SK").eq("PROFILE#MAIN") & (
            Attr("email").contains(query) | Attr("given_name").contains(query) | Attr("PK").contains(q)
        ),
        Limit=limit
    )
    items = resp.get("Items", [])
    out = []
    for it in items:
        out.append({
            "sub": it["PK"].split("#",1)[1],
            "email": it.get("email",""),
            "given_name": it.get("given_name","")
        })
    return out

# ---------- CONNECTIONS & DMs ----------

def connect_users(a_sub: str, b_sub: str):
    now = _now_iso()
    table.put_item(Item={"PK": f"USER#{a_sub}", "SK": f"CONN#{b_sub}", "created_at": now, "type":"conn"})
    table.put_item(Item={"PK": f"USER#{b_sub}", "SK": f"CONN#{a_sub}", "created_at": now, "type":"conn"})
    return {"ok": True}

def list_connections(sub: str, limit: int = 50) -> List[str]:
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{sub}") & Key("SK").begins_with("CONN#"),
        Limit=limit, ScanIndexForward=False
    )
    items = resp.get("Items", [])
    return [i["SK"].split("#",1)[1] for i in items]

def _convo_id(a: str, b: str) -> str:
    return "|".join(sorted([a,b]))

def send_dm(sender_sub: str, receiver_sub: str, text: str) -> Dict[str, Any]:
    cid = _convo_id(sender_sub, receiver_sub)
    ts = _now_iso()
    msg_id = str(uuid.uuid4())
    msg = {
        "PK": f"DM#{cid}", "SK": f"MSG#{ts}#{msg_id}",
        "from": sender_sub, "to": receiver_sub, "text": text[:2000], "created_at": ts, "type":"dm",
        "msg_id": msg_id
    }
    table.put_item(Item=msg)
    table.put_item(Item={"PK": f"USER#{sender_sub}", "SK": f"DM#{cid}", "type":"dm_ptr", "updated_at": ts})
    table.put_item(Item={"PK": f"USER#{receiver_sub}", "SK": f"DM#{cid}", "type":"dm_ptr", "updated_at": ts})
    return {"ok": True, "msg": {"from": sender_sub, "to": receiver_sub, "text": text, "created_at": ts, "msg_id": msg_id}}


def list_dm(sub_a: str, sub_b: str, limit: int = 50) -> List[Dict[str, Any]]:
    cid = _convo_id(sub_a, sub_b)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"DM#{cid}") & Key("SK").begins_with("MSG#"),
        Limit=limit, ScanIndexForward=False
    )
    return resp.get("Items", [])



# --- Conversation summaries (name + last message) ---

def get_profile(sub: str):
    resp = table.get_item(Key={"PK": f"USER#{sub}", "SK": "PROFILE#MAIN"})
    it = resp.get("Item") or {}
    return {"sub": sub, "email": it.get("email",""), "given_name": it.get("given_name","")}

def list_dm_conversations(sub: str, limit: int = 20):
    # Find my DM rooms (pointers live under USER#<sub> / SK begins DM#)
    resp = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{sub}") & Key("SK").begins_with("DM#"),
        Limit=limit, ScanIndexForward=False
    )
    ptrs = resp.get("Items", [])
    convs = []
    for p in ptrs:
        cid = p["SK"].split("#", 1)[1]  # "<a>|<b>"
        a, b = cid.split("|", 1)
        peer = b if a == sub else a

        # newest message in this convo
        r = table.query(
            KeyConditionExpression=Key("PK").eq(f"DM#{cid}") & Key("SK").begins_with("MSG#"),
            Limit=1, ScanIndexForward=False
        )
        last = (r.get("Items") or [None])[0]
        prof = get_profile(peer)
        convs.append({
            "peer_sub": peer,
            "peer_name": prof.get("given_name") or prof.get("email") or peer,
            "last_text": last["text"] if last else "",
            "last_at": last["created_at"] if last else p.get("updated_at")
        })

    # sort by last message time (desc)
    convs.sort(key=lambda x: x.get("last_at") or "", reverse=True)
    return convs
