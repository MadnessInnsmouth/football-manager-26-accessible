import asyncio
import json
import secrets
from dataclasses import dataclass, field
from typing import Dict, Optional

HOST = "0.0.0.0"
PORT = 34888


@dataclass
class ClientConn:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    room_code: Optional[str] = None
    role: Optional[str] = None
    club_name: str = ""
    country: str = ""


@dataclass
class Room:
    code: str
    host: Optional[ClientConn] = None
    guest: Optional[ClientConn] = None
    state: dict = field(default_factory=dict)


rooms: Dict[str, Room] = {}


def make_code() -> str:
    while True:
        code = secrets.token_hex(3).upper()
        if code not in rooms:
            return code


async def send(writer: asyncio.StreamWriter, payload: dict):
    writer.write((json.dumps(payload) + "\n").encode("utf-8"))
    await writer.drain()


async def broadcast(room: Room, payload: dict):
    for client in [room.host, room.guest]:
        if client:
            await send(client.writer, payload)


async def handle_message(client: ClientConn, msg: dict):
    msg_type = msg.get("type")
    payload = msg.get("payload", {}) or {}

    if msg_type == "create_room":
        code = make_code()
        room = Room(code=code)
        room.host = client
        client.room_code = code
        client.role = "host"
        client.club_name = payload.get("club_name", "Host Club")
        client.country = payload.get("country", "England")
        rooms[code] = room
        await send(client.writer, {"type": "room_created", "payload": {"room_code": code}})
        return

    if msg_type == "join_room":
        code = str(payload.get("room_code", "")).upper().strip()
        room = rooms.get(code)
        if not room:
            await send(client.writer, {"type": "error", "payload": {"message": "Room not found."}})
            return
        if room.guest is not None:
            await send(client.writer, {"type": "error", "payload": {"message": "Room already full."}})
            return
        room.guest = client
        client.room_code = code
        client.role = "guest"
        client.club_name = payload.get("club_name", "Guest Club")
        client.country = payload.get("country", room.host.country if room.host else "England")
        await send(client.writer, {"type": "room_joined", "payload": {"room_code": code}})
        await broadcast(room, {
            "type": "room_ready",
            "payload": {
                "room_code": code,
                "host_club": room.host.club_name if room.host else "Host Club",
                "guest_club": room.guest.club_name if room.guest else "Guest Club",
                "country": room.host.country if room.host else client.country,
            },
        })
        return

    if msg_type == "start_match":
        room = rooms.get(client.room_code or "")
        if not room or client.role != "host":
            await send(client.writer, {"type": "error", "payload": {"message": "Only the host can start the match."}})
            return
        await broadcast(room, {"type": "start_match", "payload": payload})
        return

    if msg_type == "match_result":
        room = rooms.get(client.room_code or "")
        if room:
            await broadcast(room, {"type": "match_result", "payload": payload})
        return

    if msg_type == "ping":
        await send(client.writer, {"type": "pong", "payload": {}})
        return

    await send(client.writer, {"type": "error", "payload": {"message": f"Unknown message type: {msg_type}"}})


async def cleanup(client: ClientConn):
    code = client.room_code
    if not code:
        return
    room = rooms.get(code)
    if not room:
        return
    if room.host is client:
        room.host = None
    if room.guest is client:
        room.guest = None
    if room.host is None and room.guest is None:
        rooms.pop(code, None)
    else:
        try:
            await broadcast(room, {"type": "peer_left", "payload": {"message": "The other player disconnected."}})
        except Exception:
            pass


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    client = ClientConn(reader=reader, writer=writer)
    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break
            try:
                msg = json.loads(raw.decode("utf-8"))
            except Exception:
                await send(writer, {"type": "error", "payload": {"message": "Invalid JSON."}})
                continue
            await handle_message(client, msg)
    finally:
        await cleanup(client)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Football Manager multiplayer server listening on {addrs}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
