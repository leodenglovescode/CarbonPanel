import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.broadcast import connection_manager
from app.core.security import decode_token
from app.services.metrics.collector import metrics_collector

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = ""):
    # Authenticate via query param token
    try:
        payload = decode_token(token)
        if payload.get("scope") != "full":
            await ws.close(code=4001)
            return
    except ValueError:
        await ws.close(code=4001)
        return

    await connection_manager.connect(ws)

    # Send client preferences for process sorting
    prefs = {"process_sort": "cpu", "process_limit": 25}

    try:
        while True:
            try:
                data = await ws.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "set_prefs":
                    if "process_sort" in msg:
                        prefs["process_sort"] = msg["process_sort"]
                    if "process_limit" in msg:
                        prefs["process_limit"] = int(msg["process_limit"])
                    metrics_collector.set_prefs(
                        sort_by=prefs["process_sort"],
                        limit=prefs["process_limit"],
                    )
                elif msg.get("type") == "set_interval":
                    seconds = float(msg.get("seconds", 2.0))
                    metrics_collector.set_interval(seconds)
            except WebSocketDisconnect:
                break
            except Exception:
                break
    finally:
        connection_manager.disconnect(ws)
