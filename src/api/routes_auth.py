"""
RiskOrbit — Authentication & Session Management FastAPI Router

Provides enterprise authentication endpoints:
- POST /api/v2/ops/auth/login       — Login with credentials or demo shortcut
- GET  /api/v2/ops/auth/session     — Validate active session and permissions
- POST /api/v2/ops/auth/logout      — Invalidate current session
- GET  /api/v2/ops/auth/demo-users  — Retrieve pre-configured demo analyst accounts
"""
from __future__ import annotations

import os
import time
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from src.ops.rbac import (
    DEMO_USERS,
    authenticate_demo_user,
    AuthSession,
    DemoUserRecord,
    UserContext,
    UserRole,
    get_current_user,
    session_store,
)

router = APIRouter(prefix="/api/v2/ops/auth", tags=["Authentication & Session"])


class GoogleOAuthConfigResponse(BaseModel):
    configured: bool
    client_id: Optional[str] = None
    message: str


class GoogleLoginRequest(BaseModel):
    id_token: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None


class LoginRequest(BaseModel):
    username_or_email: str
    password: Optional[str] = None
    role: Optional[UserRole] = None
    remember_me: bool = True


class LoginResponse(BaseModel):
    token: str
    token_type: str = "Bearer"
    session_id: str
    user: UserContext
    expires_at: float


class SessionValidateResponse(BaseModel):
    valid: bool
    session_id: Optional[str] = None
    user: UserContext
    expires_at: Optional[float] = None


class LogoutResponse(BaseModel):
    status: str = "SUCCESS"
    message: str = "Session successfully terminated."


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    """
    Authenticate user via email, username, or demo user identifier.
    Returns Bearer token and validated user context with role capabilities.
    """
    identifier = req.username_or_email.strip().lower()

    # Resolve only an existing backend identity.  The request role is not an
    # authority and cannot influence the issued session role.
    demo_user: Optional[DemoUserRecord] = None
    for key, candidate in DEMO_USERS.items():
        if identifier in {key, candidate.email.lower(), candidate.user_id.lower()}:
            demo_user = authenticate_demo_user(key, req.password)
            break

    if demo_user:
        ctx = UserContext(
            user_id=demo_user.user_id,
            role=demo_user.role,
            name=demo_user.name,
            email=demo_user.email,
            title=demo_user.title,
            capabilities=demo_user.capabilities,
        )
        duration = 86400 * 7 if req.remember_me else 86400 # 7 days vs 24h
        session = session_store.create_session(ctx, duration_seconds=duration)
        return LoginResponse(
            token=session.token,
            session_id=session.session_id,
            user=ctx,
            expires_at=session.expires_at,
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")


@router.get("/session", response_model=SessionValidateResponse)
async def validate_session(
    authorization: Optional[str] = Header(default=None),
    user: UserContext = Depends(get_current_user),
) -> SessionValidateResponse:
    """
    Validate the current active session token and return identity + permissions.
    """
    session_id = None
    expires_at = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        sess = session_store.get_session(token)
        if sess:
            session_id = sess.session_id
            expires_at = sess.expires_at

    return SessionValidateResponse(
        valid=True,
        session_id=session_id or f"sess_{user.user_id}",
        user=user,
        expires_at=expires_at or (time.time() + 86400),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    authorization: Optional[str] = Header(default=None),
    user: UserContext = Depends(get_current_user),
) -> LogoutResponse:
    """
    Invalidate session token and terminate analyst session.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        session_store.invalidate_session(token)

    return LogoutResponse()


@router.get("/demo-users", response_model=List[DemoUserRecord])
async def list_demo_users() -> List[DemoUserRecord]:
    """
    List pre-seeded enterprise analyst demo accounts for quick switcher access.
    """
    return list(DEMO_USERS.values())


@router.get("/google/config", response_model=GoogleOAuthConfigResponse)
async def get_google_oauth_config() -> GoogleOAuthConfigResponse:
    """
    Return Google OAuth configuration readiness.
    Detects whether GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are configured.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if client_id and client_secret:
        return GoogleOAuthConfigResponse(
            configured=True,
            client_id=client_id,
            message="Google OAuth provider is configured and available.",
        )
    return GoogleOAuthConfigResponse(
        configured=False,
        client_id=None,
        message="Google sign-in is not configured for this environment.",
    )


@router.post("/google/login", response_model=LoginResponse)
async def google_login(req: GoogleLoginRequest) -> LoginResponse:
    """
    Authenticate via Google OAuth token/code.
    If OAuth is not configured in this environment, returns 501 Not Implemented.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google sign-in is not configured for this environment.",
        )

    # In production with configured Google OAuth:
    # Validate token against Google TokenInfo endpoint or exchange code.
    # For now, return 400 if no token provided.
    if not req.id_token and not req.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Google authentication token or authorization code.",
        )

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google identity validation requires external network access to Google IdP.",
    )
