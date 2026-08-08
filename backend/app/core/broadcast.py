from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def send_to(self, ws: WebSocket, data: str) -> bool:
        """Send to one connection, dropping it if the send fails.

        Needed because clients no longer all receive an identical payload —
        process sort order and limit are per-client, so the collector builds
        a payload per distinct preference set and addresses them individually.
        """
        try:
            await ws.send_text(data)
            return True
        except Exception:
            self.active.discard(ws)
            return False

    async def broadcast(self, data: str) -> None:
        dead: set[WebSocket] = set()
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self.active -= dead


connection_manager = ConnectionManager()
