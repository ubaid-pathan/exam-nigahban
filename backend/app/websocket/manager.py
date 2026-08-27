"""Connection manager for the real-time admin alerts WebSocket channel.

Phase 7F-1 establishes the infrastructure only: this manager tracks
connected admin sockets and can broadcast a JSON-compatible message to all
of them, but nothing in the application calls broadcast() yet. Wiring
monitoring-event creation / evidence review to actually call it is a later
phase.
"""

from __future__ import annotations

import logging
from typing import Literal, TypedDict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MonitoringAlertMessage(TypedDict):
    """The JSON message contract a future phase will pass to
    ConnectionManager.broadcast() when a monitoring event or evidence
    review changes. Defined now so later phases have one agreed shape to
    build against; nothing constructs or sends this yet.

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
