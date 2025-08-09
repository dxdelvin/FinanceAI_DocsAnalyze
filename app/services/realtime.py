from collections import defaultdict
from typing import Dict, Set
from fastapi import WebSocket

def convo_id(a: str, b: str) -> str:
    return "|".join(sorted([a, b]))

class DMManager:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, ws: WebSocket, me: str, peer: str):
        await ws.accept()
        self.rooms[convo_id(me, peer)].add(ws)

    def disconnect(self, ws: WebSocket, me: str, peer: str):
        rid = convo_id(me, peer)
        room = self.rooms.get(rid)
        if not room: return
        room.discard(ws)
        if not room:
            self.rooms.pop(rid, None)

    async def broadcast(self, me: str, peer: str, payload: dict):
        rid = convo_id(me, peer)
        room = list(self.rooms.get(rid, set()))
        dead = []
        for ws in room:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.rooms[rid].discard(ws)

dm_manager = DMManager()
