# Real-Time Chat Application

A Python WebSocket chat-system project with private chats, group chats,
offline message storage, delivery/read receipts and ordered messages.

## Files
- `server.py` — starts the WebSocket server and routes requests
- `client.py` — terminal client for testing
- `accounts.py` — registration and password hashing
- `chat_service.py` — chat and receipt logic
- `socket_manager.py` — active WebSocket connections
- `database.py` — SQLite storage and message sequence numbers
- `models.py` — message data structure

## Run (Windows / VS Code)

Open PowerShell in this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

Open another terminal for each user:

```powershell
.\.venv\Scripts\python.exe client.py alice password123
.\.venv\Scripts\python.exe client.py bob password123
```

The client creates an account automatically on the first run. It prints each
user's ID. Use that ID to open a private chat:

```text
/dm BOBS_USER_ID
```

The server response prints the new room ID. Select it in the client:

```text
/room ROOM_ID
```

Then type messages. For a group:

```text
/group project BOBS_USER_ID,ANOTHER_USER_ID
```

Other commands: `/history`, `/read 5`, `/quit`.

## How the design works

- WebSockets provide live two-way communication.
- A user can have more than one connected device.
- SQLite stores messages and each recipient's delivery state.
- Offline messages remain queued until the recipient reconnects.
- Each room assigns increasing message numbers inside a database transaction.
- Receipt states move forward from `sent` to `delivered` to `read`.

## Scope

This is an educational prototype, not a production messaging service. It does
not include end-to-end encryption, file sharing, push notifications, robust
session tokens, or multi-server coordination. Add those before real deployment.
