import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import log_event
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutResponse, Token
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.username == payload.username).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        log_event(
            "auth.login.failed",
            level=logging.WARNING,
            username=payload.username,
            reason="unknown_user" if user is None else "bad_password",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.status:
        log_event(
            "auth.login.rejected",
            level=logging.WARNING,
            username=user.username,
            reason="account_inactive",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
        )

    log_event("auth.login.succeeded", username=user.username, role=user.role)
    access_token = create_access_token(subject=user.username, role=user.role)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", response_model=LogoutResponse)
def logout(current_user: User = Depends(get_current_user)) -> LogoutResponse:
    log_event("auth.logout", username=current_user.username)
    return LogoutResponse()
