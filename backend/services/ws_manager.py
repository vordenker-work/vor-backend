import json
import logging
from fastapi import WebSocket

logger = logging.getLogger("ws_manager")


class ConnectionManager:
    """In-memory WebSocket connection registry for live notifications and chat."""

    def __init__(self) -> None:
        self.connections: list[dict] = []

    async def connect(self, websocket: WebSocket, email: str | None = None) -> None:
        await websocket.accept()
        self.connections.append({"websocket": websocket, "email": email})
        logger.info(f"WS connected (email={email}, active={len(self.connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections = [c for c in self.connections if c["websocket"] != websocket]
        logger.info(f"WS disconnected (active={len(self.connections)})")

    async def broadcast(self, data: dict) -> None:
        message = json.dumps(data)
        for conn in list(self.connections):
            try:
                await conn["websocket"].send_text(message)
            except Exception:
                self.disconnect(conn["websocket"])

    async def send_to_email(self, email: str | None, data: dict) -> None:
        if not email:
            return
        target = email.lower().strip()
        message = json.dumps(data)
        for conn in list(self.connections):
            if (conn.get("email") or "").lower().strip() == target:
                try:
                    await conn["websocket"].send_text(message)
                except Exception:
                    self.disconnect(conn["websocket"])


ws_manager = ConnectionManager()
