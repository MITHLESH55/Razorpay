"""
RiskOrbit — Authentication & Session Management FastAPI Router

Provides enterprise authentication endpoints:
- POST /api/v2/ops/auth/login       — Login with credentials
- GET  /api/v2/ops/auth/session     — Validate active session and permissions
- POST /api/v2/ops/auth/logout      — Invalidate current session
- GET  /api/v2/ops/auth/demo-users  — Retrieve pre-configured demo analyst accounts
"""
from __future__ import annotations

import os
import time
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from src.ops.rbac import (
    GENERIC_AUTH_ERROR,
    authenticate_user,
    AuthSession,
    DemoUserRecord,
    UserContext,
    UserRole,
    get_current_user,
    ROLE_HIERARCHY,
    session_store,
    user_repository,
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
    password: str
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


class UserProvisionRequest(BaseModel):
    username: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)
    role: UserRole = UserRole.ANALYST
    name: str = Field(min_length=1)
    title: Optional[str] = None
    department: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    status: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(default=None, min_length=1)


class UserAdminResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: UserRole
    name: str
    title: Optional[str] = None
    department: Optional[str] = None
    capabilities: List[str]
    status: str
    created_at: str
    updated_at: str
    last_login_at: Optional[str] = None
    email_verified: bool


def _user_admin_response(user: Any) -> UserAdminResponse:
    return UserAdminResponse(
        user_id=user["user_id"], username=user["username"], email=user["email"],
        role=UserRole(user["role"]), name=user["name"], title=user["title"],
        department=user["department"], capabilities=__import__("json").loads(user["capabilities"]),
        status=user["status"], created_at=user["created_at"], updated_at=user["updated_at"],
        last_login_at=user["last_login_at"], email_verified=bool(user["email_verified"]),
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest) -> LoginResponse:
    """
    Authenticate user via email or username.
    Returns Bearer token and validated user context with role capabilities.
    """
    identifier = req.username_or_email.strip().lower()
    password = req.password

    ctx = authenticate_user(identifier, password)
    if ctx:
        duration = 86400 * 7 if req.remember_me else 86400 # 7 days vs 24h
        session = session_store.create_session(ctx, duration_seconds=duration)
        return LoginResponse(
            token=session.token,
            session_id=session.session_id,
            user=ctx,
            expires_at=session.expires_at,
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_ERROR)


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
    user_repository.record_security_event("LOGOUT", user.user_id, user.user_id)

    return LogoutResponse()


@router.get("/demo-users", response_model=List[DemoUserRecord])
async def list_demo_users() -> List[DemoUserRecord]:
    """
    List pre-seeded enterprise analyst demo accounts for quick switcher access.
    """
    return [user_repository.to_demo_record(user) for user in user_repository.list_users()]


@router.get("/users", response_model=List[UserAdminResponse])
async def list_users(user: UserContext = Depends(get_current_user)) -> List[UserAdminResponse]:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access is required.")
    return [_user_admin_response(account) for account in user_repository.list_users()]


@router.post("/users", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_user(req: UserProvisionRequest, user: UserContext = Depends(get_current_user)) -> UserAdminResponse:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access is required.")
    try:
        account = user_repository.create_user(
            username=req.username, email=req.email, password=req.password, role=req.role,
            name=req.name, title=req.title, department=req.department,
            capabilities=req.capabilities, actor_id=user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _user_admin_response(account)


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(user_id: str, req: UserUpdateRequest, user: UserContext = Depends(get_current_user)) -> UserAdminResponse:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access is required.")
    if req.status is not None and req.status not in {"ACTIVE", "DISABLED"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Status must be ACTIVE or DISABLED.")
    if user_id == user.user_id and req.role is not None and req.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The active administrator cannot remove their own administrator role.")
    try:
        account = user_repository.update_user(user_id, user.user_id, status_value=req.status, role=req.role, password=req.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _user_admin_response(account)


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
