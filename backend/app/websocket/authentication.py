"""WebSocket authentication for the admin alerts channel.

WebSocket routes don't go through FastAPI's HTTPBearer/Depends security
flow the way HTTP routes do (see app.api.deps.get_current_user /
require_admin), so this module re-implements just enough of that same
check for a WebSocket connection: the token is read from a query
parameter (?token=<JWT>) instead of an Authorization header, and the
checks are performed directly against the existing decode_access_token
function and User model -- no second JWT implementation.
"""

from __future__ import annotations

import jwt
from fastapi import WebSocket, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import User


class WebSocketAuthError(Exception):
    """Raised when a WebSocket connection fails authentication.

    Callers must close the socket with `code`/`reason` and must not call
    `websocket.accept()` beforehand.
    """

    def __init__(self, code: int, reason: str) -> None:
        self.code = code
        self.reason = reason
        super().__init__(reason)


async def authenticate_admin_websocket(websocket: WebSocket, db: Session) -> User:
    """Authenticates a WebSocket connection for the admin alerts channel.

    Mirrors the checks in app.api.deps.get_current_user + require_admin
    (valid signature, not expired, active account, admin role), raising
    WebSocketAuthError on the first failed check instead of HTTPException.
    """
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketAuthError(
            status.WS_1008_POLICY_VIOLATION, "Missing authentication token"
        )

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise WebSocketAuthError(
            status.WS_1008_POLICY_VIOLATION, "Invalid or expired token"
        )

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()

    if user is None or not user.status:
        raise WebSocketAuthError(
            status.WS_1008_POLICY_VIOLATION, "Invalid or expired token"
        )

    if user.role != "admin":
        raise WebSocketAuthError(
            status.WS_1008_POLICY_VIOLATION, "Admin access required"
        )

    return user
