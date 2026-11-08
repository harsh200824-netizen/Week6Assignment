import asyncio, json
from collections import defaultdict

class SocketManager:
    def __init__(self):
        self.connections = defaultdict(set)
        self.lock = asyncio.Lock()

    async def add(self, uid, ws):
        async with self.lock: self.connections[uid].add(ws)

    async def remove(self, uid, ws):
        async with self.lock:
            self.connections[uid].discard(ws)
            if not self.connections[uid]: self.connections.pop(uid,None)

    async def send(self, uid, event):
        async with self.lock: targets = list(self.connections.get(uid,()))
        if not targets: return False
        async def one(ws):
            try:
                await ws.send(json.dumps(event))
                return True
            except Exception: return False
        results = await asyncio.gather(*(one(ws) for ws in targets))
        return any(results)
