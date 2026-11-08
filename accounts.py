import hashlib, secrets, uuid

class Accounts:
    def __init__(self, db): self.db = db

    @staticmethod
    def hash_password(password, salt=None):
        salt = salt or secrets.token_hex(12)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000).hex()
        return salt + "$" + digest

    def register(self, name, password):
        name = name.strip()
        if not name or len(name)>30 or len(password)<6: return None
        uid = uuid.uuid4().hex
        if self.db.add_user(uid,name,self.hash_password(password)):
            return {"id":uid,"username":name}
        return None

    def login(self, name, password):
        row = self.db.user_by_name(name.strip())
        if not row: return None
        salt = row["password"].split("$",1)[0]
        if secrets.compare_digest(self.hash_password(password,salt),row["password"]):
            return {"id":row["id"],"username":row["name"]}
        return None
