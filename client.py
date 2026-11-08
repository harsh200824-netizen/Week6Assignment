import asyncio, json, sys, websockets

SERVER = "ws://localhost:8765"

async def main():
    if len(sys.argv)!=3:
        print("Usage: python client.py USERNAME PASSWORD"); return
    name,password = sys.argv[1],sys.argv[2]
    async with websockets.connect(SERVER) as ws:
        login = {"action":"login","username":name,"password":password}
        await ws.send(json.dumps(login))
        result = json.loads(await ws.recv())
        if not result.get("ok"):
            await ws.send(json.dumps({"action":"register","username":name,"password":password}))
            result = json.loads(await ws.recv())
            if not result.get("ok"):
                print("Registration failed. Password must be 6+ characters and username unique."); return
            await ws.send(json.dumps(login))
            result = json.loads(await ws.recv())
        uid = result["user"]["id"]
        print(f"Logged in as {name}. User ID: {uid}")
        print("Commands: /dm USER_ID | /group TITLE ID,ID | /room ROOM_ID | /history | /read N | /quit")

        async def reader():
            while True:
                try:
                    frame = json.loads(await ws.recv())
                    if frame.get("event")=="message":
                        m=frame["message"]
                        suffix=" [offline]" if frame.get("offline") else ""
                        print(f"\n[{m['number']}] {m['sender'][:6]}: {m['text']}{suffix}\n> ",end="",flush=True)
                    elif frame.get("event")=="receipt":
                        print(f"\n{frame['state']} receipt from {frame['recipient'][:6]}\n> ",end="",flush=True)
                    else:
                        print("\nServer response:",frame,"\n> ",end="",flush=True)
                except Exception: break

        task=asyncio.create_task(reader())
        room_id=None
        loop=asyncio.get_running_loop()
        try:
            while True:
                line=(await loop.run_in_executor(None,input,"> ")).strip()
                if line=="/quit": break
                if line.startswith("/dm "):
                    request={"action":"private","other_user":line[4:].strip()}
                elif line.startswith("/group "):
                    parts=line[7:].split(maxsplit=1)
                    if len(parts)!=2:
                        print("Format: /group TITLE USER_ID,USER_ID"); continue
                    request={"action":"group","title":parts[0],"members":parts[1].split(",")}
                elif line.startswith("/room "):
                    room_id=line[6:].strip()
                    print("Active room:",room_id); continue
                elif line=="/history":
                    if not room_id: print("Choose a room first."); continue
                    request={"action":"history","room_id":room_id}
                elif line.startswith("/read "):
                    if not room_id: print("Choose a room first."); continue
                    request={"action":"read","room_id":room_id,"through":int(line.split()[1])}
                elif line and room_id:
                    request={"action":"send","room_id":room_id,"text":line}
                else:
                    print("Open a chat first."); continue
                await ws.send(json.dumps(request))
                if request["action"] in ("private","group"):
                    print("Room details will appear in the server response above.")
        finally:
            task.cancel()

if __name__=="__main__": asyncio.run(main())
