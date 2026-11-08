from dataclasses import dataclass
import time, uuid

@dataclass
class ChatMessage:
    id: str
    room_id: str
    sender: str
    text: str
    number: int = 0
    created: float = 0.0

    @classmethod
    def create(cls, room_id, sender, text):
        return cls(uuid.uuid4().hex, room_id, sender, text, 0, time.time())

    def as_dict(self):
        return {"id": self.id, "room_id": self.room_id, "sender": self.sender,
                "text": self.text, "number": self.number, "created": self.created}
