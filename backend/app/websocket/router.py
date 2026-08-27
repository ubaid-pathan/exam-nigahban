"""WebSocket route for real-time administrator alerts.

Phase 7F-1: infrastructure only. This endpoint authenticates, tracks, and
keeps admin connections alive -- it does not yet broadcast any real
monitoring/evidence events (see app/websocket/manager.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.websocket.authentication import WebSocketAuthError, authenticate_admin_websocket
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/admin/alerts")
async def admin_alerts(websocket: WebSocket, db: Session = Depends(get_db)) -> None:
    try:
        await authenticate_admin_websocket(websocket, db)
    except WebSocketAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Blocks (no busy-waiting/polling) until the client sends a
            # message or disconnects. This channel is broadcast-only from
            # the server's side for now, so any inbound message is simply
            # discarded -- the receive is only here to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
