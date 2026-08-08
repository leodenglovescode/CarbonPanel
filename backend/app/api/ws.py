import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.broadcast import connection_manager
from app.core.dependencies import COOKIE_NAME, is_allowed_ws_origin
from app.core.security import decode_token
from app.services.metrics.collector import metrics_collector

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    if not is_allowed_ws_origin(ws):
        await ws.close(code=4003)
        return

    # Authenticate via the httpOnly session cookie — the browser sends it
    # automatically on the WS handshake, no token in the URL/query string.
    try:
        payload = decode_token(ws.cookies.get(COOKIE_NAME, ""))
        if payload.get("scope") != "full":
            await ws.close(code=4001)
            return
    except ValueError:
        await ws.close(code=4001)
        return

    await connection_manager.connect(ws)
    # Preferences are scoped to this connection. They used to be written
    # straight onto the collector singleton, so whichever tab spoke last set
    # the sort order and refresh rate for every other connected client.
    metrics_collector.register_ws(ws)

    try:
        while True:
            try:
                data = await ws.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "set_prefs":
                    metrics_collector.set_prefs(
                        ws,
                        sort_by=msg.get("process_sort"),
                        limit=msg.get("process_limit"),
                    )
                elif msg.get("type") == "set_interval":
                    metrics_collector.set_interval(ws, msg.get("seconds", 2.0))
            except WebSocketDisconnect:
                break
            except Exception:
                break
    finally:
        metrics_collector.unregister_ws(ws)
        connection_manager.disconnect(ws)
