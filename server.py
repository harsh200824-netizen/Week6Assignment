import asyncio, json, os, websockets
from database import Database
from accounts import Accounts
from socket_manager import SocketManager
from chat_service import ChatService

db = Database(os.getenv("CHAT_DB","chat_data.db"))
accounts = Accounts(db)
sockets = SocketManager()
chat = ChatService(db,sockets)

async def handle(user_id, req):
    action = req.get("action")
    if action == "register":
        user = accounts.register(req.get("username",""),req.get("password",""))
        return user["id"] if user else None, {"ok":bool(user),"user":user}
    if action == "login":
        user = accounts.login(req.get("username",""),req.get("password",""))
        return user["id"] if user else None, {"ok":bool(user),"user":user,
                                               "error":None if user else "invalid_login"}
    if not user_id: return None, {"ok":False,"error":"login_required"}
    if action == "private":
        rid = chat.open_private(user_id,req.get("other_user",""))
        return user_id, {"ok":bool(rid),"room_id":rid}
    if action == "group":
        rid = chat.make_group(user_id,req.get("title",""),req.get("members",[]))
        return user_id, {"ok":bool(rid),"room_id":rid}
    if action == "send":
        return user_id, await chat.send_message(user_id,req.get("room_id",""),req.get("text",""))
    if action == "history":
        rid = req.get("room_id","")
        room = db.room(rid)
        if not room or user_id not in room["members"]:
            return user_id, {"ok":False,"error":"not_a_member"}
        return user_id, {"ok":True,"messages":db.history(rid,int(req.get("limit",50)))}
    if action == "read":
        return user_id, await chat.read_messages(user_id,req.get("room_id",""),int(req.get("through",0)))
    return user_id, {"ok":False,"error":"unknown_action"}

async def connection(ws):
    user_id = None
    try:
        async for raw in ws:
            try:
                req = json.loads(raw)
                user_id, answer = await handle(user_id,req)
                if user_id:
                    await sockets.add(user_id,ws)
                    answer["offline_delivered"] = await chat.deliver_offline(user_id)
                await ws.send(json.dumps(answer))
            except (ValueError,TypeError,json.JSONDecodeError):
                await ws.send(json.dumps({"ok":False,"error":"invalid_request"}))
    finally:
        if user_id: await sockets.remove(user_id,ws)

async def main():
    host, port = os.getenv("CHAT_HOST","localhost"), int(os.getenv("CHAT_PORT","8765"))
    async with websockets.serve(connection,host,port,ping_interval=20):
        print(f"Chat server listening at ws://{host}:{port}")
        await asyncio.Future()

if __name__ == "__main__": asyncio.run(main())
