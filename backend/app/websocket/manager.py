"""Connection manager for the real-time admin alerts WebSocket channel.

Tracks connected admin sockets and broadcasts a JSON-compatible message to
all of them. Two callers exist: monitoring-event creation
(app/api/routes/monitoring.py::_broadcast_monitoring_event) and enforcement
actions (app/api/routes/enforcement.py::_broadcast_enforcement_action).
Both broadcast after their row is committed and swallow any failure, so a
disconnected admin can never affect the HTTP response.

For notifications aimed at ONE student's exam session rather than every
admin, see app/websocket/session_manager.py -- a separate manager, because
"deliver to one session" and "broadcast to everyone" are different enough
that sharing one implementation would complicate both.
"""

from __future__ import annotations

import logging
from typing import Literal, TypedDict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MonitoringAlertMessage(TypedDict):
    """The JSON message shape broadcast when a monitoring event is created.

    Documents the contract admin clients parse (see
    frontend/src/api/adminAlertsSocket.js, which allow-lists this type
    alongside "enforcement_action"). The route builds the dict inline
    rather than instantiating this, so treat it as the reference for the
    shape rather than as the constructor for it.

    Example:
        {
            "type": "monitoring_event",
            "event_id": 123,
            "session_id": 45,
            "severity": "high",
            "event_type": "phone_detected",
            "status": "PENDING_REVIEW",
        }
    """

    type: Literal["monitoring_event"]
    event_id: int
    session_id: int
    severity: str
    event_type: str
    status: str


class ConnectionManager:
    """Tracks connected admin WebSocket clients and broadcasts to them."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts the handshake and starts tracking the connection.

        Callers must authenticate the connection before calling this --
        this method does not check authorization itself.
        """
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Stops tracking a connection. Safe to call even if it was never
        tracked (e.g. a socket that failed during broadcast and was
        already dropped)."""
        self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        """Sends a JSON-compatible message to every connected admin.

        Iterates a snapshot of the connection set so a connection that
        fails or disconnects mid-broadcast can be safely removed without
        mutating the set while iterating it, and without a single failed
        socket aborting delivery to the rest.
        """
        for connection in list(self._connections):
            try:
                await connection.send_json(message)
            except Exception:
                logger.info("Dropping unreachable admin WebSocket during broadcast")
                self._connections.discard(connection)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()
