import sqlite3, threading, time
from models import ChatMessage

class Database:
    def __init__(self, path="chat_data.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock, self.db:
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT UNIQUE, password TEXT);
            CREATE TABLE IF NOT EXISTS rooms(id TEXT PRIMARY KEY, title TEXT, kind TEXT, next_no INTEGER DEFAULT 1);
            CREATE TABLE IF NOT EXISTS members(room_id TEXT, user_id TEXT, PRIMARY KEY(room_id,user_id));
            CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, room_id TEXT, sender TEXT,
                body TEXT, number INTEGER, created REAL, UNIQUE(room_id,number));
            CREATE TABLE IF NOT EXISTS receipts(message_id TEXT, user_id TEXT, state TEXT,
                changed REAL, PRIMARY KEY(message_id,user_id));
            CREATE INDEX IF NOT EXISTS pending_idx ON receipts(user_id,state);
            """)

    def add_user(self, uid, name, password):
        try:
            with self.lock, self.db:
                self.db.execute("INSERT INTO users VALUES(?,?,?)", (uid,name,password))
            return True
        except sqlite3.IntegrityError:
            return False

    def user_by_name(self, name):
        with self.lock:
            row = self.db.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
        return dict(row) if row else None

    def user_exists(self, uid):
        with self.lock:
            return self.db.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone() is not None

    def create_room(self, rid, title, kind, members):
        with self.lock, self.db:
            self.db.execute("INSERT INTO rooms(id,title,kind) VALUES(?,?,?)", (rid,title,kind))
            self.db.executemany("INSERT INTO members VALUES(?,?)", [(rid,u) for u in set(members)])

    def room(self, rid):
        with self.lock:
            row = self.db.execute("SELECT * FROM rooms WHERE id=?", (rid,)).fetchone()
            if not row: return None
            users = self.db.execute("SELECT user_id FROM members WHERE room_id=?", (rid,)).fetchall()
        result = dict(row)
        result["members"] = [r["user_id"] for r in users]
        return result

    def private_room(self, a, b):
        with self.lock:
            row = self.db.execute("""
                SELECT r.id FROM rooms r
                JOIN members x ON x.room_id=r.id AND x.user_id=?
                JOIN members y ON y.room_id=r.id AND y.user_id=?
                WHERE r.kind='private' LIMIT 1
            """, (a,b)).fetchone()
        return row["id"] if row else None

    def save_message(self, msg, recipients):
        with self.lock, self.db:
            row = self.db.execute("SELECT next_no FROM rooms WHERE id=?", (msg.room_id,)).fetchone()
            if not row: raise ValueError("Room not found")
            msg.number = row["next_no"]
            self.db.execute("UPDATE rooms SET next_no=? WHERE id=?", (msg.number+1,msg.room_id))
            self.db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)",
                (msg.id,msg.room_id,msg.sender,msg.text,msg.number,msg.created))
            now = time.time()
            self.db.executemany("INSERT INTO receipts VALUES(?,?,?,?)",
                [(msg.id,u,"sent",now) for u in recipients if u != msg.sender])
        return msg

    def history(self, rid, limit=50):
        with self.lock:
            rows = self.db.execute("SELECT * FROM messages WHERE room_id=? ORDER BY number DESC LIMIT ?",
                                   (rid,limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    def pending(self, uid):
        with self.lock:
            rows = self.db.execute("""
                SELECT m.* FROM messages m JOIN receipts r ON r.message_id=m.id
                WHERE r.user_id=? AND r.state='sent' ORDER BY m.room_id,m.number
            """, (uid,)).fetchall()
        return [dict(r) for r in rows]

    def receipt(self, mid, uid, state):
        rank = {"sent":0,"delivered":1,"read":2}
        with self.lock, self.db:
            row = self.db.execute("SELECT state FROM receipts WHERE message_id=? AND user_id=?",
                                  (mid,uid)).fetchone()
            if row and rank[state] > rank[row["state"]]:
                self.db.execute("UPDATE receipts SET state=?,changed=? WHERE message_id=? AND user_id=?",
                                (state,time.time(),mid,uid))

    def mark_read(self, rid, uid, through):
        with self.lock, self.db:
            rows = self.db.execute("""
                SELECT m.id FROM messages m JOIN receipts r ON r.message_id=m.id AND r.user_id=?
                WHERE m.room_id=? AND m.sender<>? AND m.number<=? AND r.state<>'read'
            """, (uid,rid,uid,through)).fetchall()
            now = time.time()
            self.db.executemany("UPDATE receipts SET state='read',changed=? WHERE message_id=? AND user_id=?",
                                [(now,r["id"],uid) for r in rows])
        return [r["id"] for r in rows]

    def message_info(self, mid):
        with self.lock:
            row = self.db.execute("SELECT id,room_id,sender,number FROM messages WHERE id=?", (mid,)).fetchone()
        return dict(row) if row else None
