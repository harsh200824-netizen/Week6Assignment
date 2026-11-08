import uuid
from models import ChatMessage

class ChatService:
    def __init__(self, db, sockets):
        self.db, self.sockets = db, sockets

    def open_private(self, user, other):
        if user == other or not self.db.user_exists(other): return None
        old = self.db.private_room(user,other)
        if old: return old
        rid = uuid.uuid4().hex
        self.db.create_room(rid,"Private chat","private",[user,other])
        return rid

    def make_group(self, creator, title, members):
        people = set(members) | {creator}
        if not title.strip() or any(not self.db.user_exists(x) for x in people): return None
        rid = uuid.uuid4().hex
        self.db.create_room(rid,title.strip(),"group",people)
        return rid

    async def send_message(self, sender, rid, text):
        room = self.db.room(rid)
        if not room or sender not in room["members"]:
            return {"ok":False,"error":"not_a_member"}
        if not text.strip() or len(text)>4000:
            return {"ok":False,"error":"invalid_message"}
        msg = self.db.save_message(ChatMessage.create(rid,sender,text),room["members"])
        for recipient in room["members"]:
            if recipient == sender: continue
            event = {"event":"message","message":msg.as_dict()}
            if await self.sockets.send(recipient,event):
                self.db.receipt(msg.id,recipient,"delivered")
                await self.notify(msg.id,recipient,"delivered")
        return {"ok":True,"message":msg.as_dict()}

    async def notify(self, mid, recipient, state):
        info = self.db.message_info(mid)
        if info:
            await self.sockets.send(info["sender"], {"event":"receipt","message_id":mid,
                "room_id":info["room_id"],"recipient":recipient,"state":state})

    async def deliver_offline(self, uid):
        count = 0
        for row in self.db.pending(uid):
            event = {"event":"message","offline":True,"message":{
                "id":row["id"],"room_id":row["room_id"],"sender":row["sender"],
                "text":row["body"],"number":row["number"],"created":row["created"]}}
            if await self.sockets.send(uid,event):
                self.db.receipt(row["id"],uid,"delivered")
                await self.notify(row["id"],uid,"delivered")
                count += 1
        return count

    async def read_messages(self, uid, rid, through):
        room = self.db.room(rid)
        if not room or uid not in room["members"]:
            return {"ok":False,"error":"not_a_member"}
        ids = self.db.mark_read(rid,uid,through)
        for mid in ids: await self.notify(mid,uid,"read")
        return {"ok":True,"count":len(ids)}
