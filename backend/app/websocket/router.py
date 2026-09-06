"""WebSocket route for real-time administrator alerts.

Phase 7F-1: infrastructure only. This endpoint authenticates, tracks, and
keeps admin connections alive -- it does not yet broadcast any real
monitoring/evidence events (see app/websocket/manager.py).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.websocket.authentication import (
    WebSocketAuthError,
    authenticate_admin_websocket,
    authenticate_student_session_websocket,
)
from app.websocket.manager import manager
from app.websocket.session_manager import session_manager

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


@router.websocket("/ws/student/sessions/{session_id}")
async def student_session_updates(
    websocket: WebSocket, session_id: int, db: Session = Depends(get_db)
) -> None:
    """Real-time nudges for one student's own exam session.

    Exists so an invigilator's pause or cancellation reaches the candidate
    immediately instead of on their next poll. The channel never carries
    enforcement state -- only "re-read your session" -- so the student
    client always applies enforcement from the authoritative API response
    (see app/websocket/session_manager.py).
    """
    try:
        await authenticate_student_session_websocket(websocket, session_id, db)
    except WebSocketAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    await session_manager.connect(session_id, websocket)
    try:
        while True:
            # Server-to-client only; the receive exists purely to detect
            # disconnects, exactly as in the admin channel above.
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect(session_id, websocket)
