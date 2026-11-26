import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.database import SessionLocal
from core.security import decode_token_claims
from models import models
from services.ws_manager import ws_manager

logger = logging.getLogger("ws_router")
router = APIRouter(tags=["WebSocket"])


def _resolve_email_from_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        subject_id, role = decode_token_claims(token)
    except ValueError:
        return None

    db = SessionLocal()
    try:
        if role == "recruiter":
            rec = db.query(models.Recruiter).filter(models.Recruiter.id == subject_id).first()
            return rec.email if rec else None
        stu = db.query(models.Student).filter(models.Student.id == subject_id).first()
        return stu.email if stu else None
    finally:
        db.close()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = None,
    email: str | None = None,
):
    resolved_email = _resolve_email_from_token(token) or email
    await ws_manager.connect(websocket, resolved_email)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                if data.get("type") == "chat":
                    msg = str(data.get("message", "")).strip()
                    if not msg:
                        continue
                    await ws_manager.broadcast(
                        {
                            "type": "chat",
                            "username": str(data.get("username") or "Ẩn danh")[:80],
                            "message": msg[:2000],
                            "timestamp": datetime.now(timezone.utc).strftime("%H:%M"),
                        }
                    )
            except Exception as e:
                logger.warning("Failed to parse WS payload: %s", e)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
