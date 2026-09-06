"""Connection manager for per-exam-session student notifications.

Deliberately separate from app/websocket/manager.py rather than an
extension of it. That manager broadcasts one message to every connected
admin; this one delivers to exactly the sockets watching a single exam
session, which is different enough in semantics that folding them together
would complicate the working admin channel for no benefit.

What is sent here is only ever a NUDGE -- "your session changed, re-read
it" -- never the enforcement state itself. The student client responds by
re-fetching GET /api/student/sessions/{id}, so the server stays the single
source of truth and a replayed or spoofed frame can never place a student
into an enforcement state the API did not authorise. It also means the
push path and the polling fallback apply enforcement through exactly one
code path, so they cannot drift apart.
"""

from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# The only message this channel sends. Carries no enforcement detail on
# purpose (see the module docstring).
SESSION_UPDATED = "session_updated"


class SessionConnectionManager:
    """Tracks student sockets grouped by the exam session they watch."""

    def __init__(self) -> None:
        self._by_session: dict[int, set[WebSocket]] = {}

    async def connect(self, session_id: int, websocket: WebSocket) -> None:
        """Accepts the handshake and starts tracking the connection.

        Callers must authenticate the connection AND verify the student
        owns `session_id` before calling this -- no check happens here.
        """
        await websocket.accept()
        self._by_session.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: int, websocket: WebSocket) -> None:
        """Stops tracking a connection, dropping the session's entry once
        it has no sockets left so the map cannot grow without bound across
        a long run of exams. Safe to call for an untracked socket."""
        connections = self._by_session.get(session_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._by_session.pop(session_id, None)

    async def notify_session(self, session_id: int) -> None:
        """Nudges every socket watching one session to re-read it.

        Iterates a snapshot so a socket that fails mid-send can be dropped
        without mutating the set under iteration, and so one dead
        connection never prevents delivery to the rest -- mirroring
        ConnectionManager.broadcast.
        """
        for connection in list(self._by_session.get(session_id, ())):
            try:
                await connection.send_json(
                    {"type": SESSION_UPDATED, "session_id": session_id}
                )
            except Exception:
                logger.info(
                    "Dropping unreachable student WebSocket for session %s",
                    session_id,
                )
                self.disconnect(session_id, connection)

    def connection_count(self, session_id: int) -> int:
        return len(self._by_session.get(session_id, ()))


session_manager = SessionConnectionManager()
