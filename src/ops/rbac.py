"""
RiskOrbit — Role-Based Access Control (RBAC) & Session Authentication Module

Defines analyst roles, credentials, demo identities, and session tokens.
Enforces security rules strictly on the backend:
  - VIEWER: Read-only access to overview, queues, cases, graphs, and evaluation.
  - ANALYST: Perform investigations, approve low-impact actions (2FA, Delay), record feedback.
  - SENIOR_ANALYST: Approve high-impact actions (Block, Restrict, Freeze Ring), edit/override recommendations.
  - ADMIN: Full access including system controls (Kill Switch, Shadow Mode, Safe Degradation).
"""
from __future__ import annotations

import secrets
import hmac
import time
from enum import Enum
from typing import Dict, List, Optional
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """Supported user roles in RiskOrbit operations."""
    VIEWER = "VIEWER"
    ANALYST = "ANALYST"
    SENIOR_ANALYST = "SENIOR_ANALYST"
    ADMIN = "ADMIN"


class UserContext(BaseModel):
    """Authenticated user context."""
    user_id: str
    role: UserRole
    name: str
    email: Optional[str] = None
    title: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class DemoUserRecord(BaseModel):
    """Pre-configured demo identity with metadata."""
    user_id: str
    role: UserRole
    name: str
    email: str
    title: str
    department: str
    password_hint: str
    capabilities: List[str]


class AuthSession(BaseModel):
    """Active user session record."""
    session_id: str
    token: str
    user: UserContext
    created_at: float
    expires_at: float


# Role permission hierarchy mapping
ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.VIEWER: 1,
    UserRole.ANALYST: 2,
    UserRole.SENIOR_ANALYST: 3,
    UserRole.ADMIN: 4,
}

# Action approval permissions
HIGH_IMPACT_ACTIONS = {"BLOCK_TRANSACTION", "RESTRICT_ACCOUNT", "FREEZE_RING", "HARD_BLOCK_ACCOUNT"}
LOW_IMPACT_ACTIONS = {"ALLOW", "STEP_UP_2FA", "DELAY_SETTLEMENT", "MANUAL_REVIEW", "MONITOR"}

# Pre-seeded enterprise demo profiles
DEMO_USERS: dict[str, DemoUserRecord] = {
    "analyst_01": DemoUserRecord(
        user_id="analyst_01",
        role=UserRole.ANALYST,
        name="Sarah Chen",
        email="sarah.chen@riskorbit.internal",
        title="Fraud Risk Analyst",
        department="Trust & Safety Operations",
        password_hint="Standard password or quick demo access",
        capabilities=[
            "Queue Triage & Case Search",
            "Low-Impact Action Approvals (2FA, Delay)",
            "Analyst Feedback & Ground-Truth Adjudication",
            "Evidence Graph & Timeline Inspection",
        ],
    ),
    "senior_analyst_01": DemoUserRecord(
        user_id="senior_analyst_01",
        role=UserRole.SENIOR_ANALYST,
        name="Marcus Vance",
        email="marcus.vance@riskorbit.internal",
        title="Senior Risk Strategist",
        department="Fraud Policy & Graph Intelligence",
        password_hint="Standard password or quick demo access",
        capabilities=[
            "All Standard Analyst Capabilities",
            "High-Impact Action Approvals (Block, Restrict, Freeze Ring)",
            "Policy Decision Overrides & Edit Actions",
            "Counterfactual Policy Simulation Workbench",
        ],
    ),
    "admin_01": DemoUserRecord(
        user_id="admin_01",
        role=UserRole.ADMIN,
        name="Elena Rostova",
        email="elena.rostova@riskorbit.internal",
        title="Chief Information Security Officer",
        department="Risk Engineering & Governance",
        password_hint="Standard password or quick demo access",
        capabilities=[
            "Complete Enterprise System Access",
            "Emergency Graph Kill Switch Activation",
            "Safe Mode Degradation Controls",
            "Shadow Mode Policy Activation",
        ],
    ),
    "viewer_01": DemoUserRecord(
        user_id="viewer_01",
        role=UserRole.VIEWER,
        name="Audit & Compliance Officer",
        email="audit.read@riskorbit.internal",
        title="Independent Regulatory Auditor",
        department="Model Risk & Regulatory Oversight",
        password_hint="Standard password or quick demo access",
        capabilities=[
            "Read-Only Operational Dashboard",
            "Held-Out Evaluation Metrics Inspection",
            "Immutable Cryptographic Audit Ledger Access",
            "Distribution Drift & Stability Verification",
        ],
    ),
}


class SessionStore:
    """Thread-safe active session token storage."""
    def __init__(self):
        self._sessions: dict[str, AuthSession] = {}

    def create_session(self, user_context: UserContext, duration_seconds: int = 86400) -> AuthSession:
        token = f"tok_{secrets.token_urlsafe(24)}"
        session_id = f"sess_{secrets.token_hex(8)}"
        session = AuthSession(
            session_id=session_id,
            token=token,
            user=user_context,
            created_at=time.time(),
            expires_at=time.time() + duration_seconds,
        )
        self._sessions[token] = session
        return session

    def get_session(self, token: str) -> Optional[AuthSession]:
        session = self._sessions.get(token)
        if session:
            if time.time() > session.expires_at:
                del self._sessions[token]
                return None
            return session
        return None

    def invalidate_session(self, token: str) -> bool:
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False


session_store = SessionStore()

# This demonstration deployment intentionally supports password-free demo cards.
# Credential logins still validate a server-side value; it is never sent to or
# stored by the browser.  Replace this with the enterprise IdP in production.
DEMO_PASSWORD = "password123"


def authenticate_demo_user(identifier: str, password: Optional[str]) -> Optional[DemoUserRecord]:
    """Return a known demo identity only after credential validation.

    An omitted password is the explicitly supported quick-demo flow.  A supplied
    password must be correct so malformed credential submissions cannot obtain a
    session.  The requested frontend role is deliberately not an input here.
    """
    demo = DEMO_USERS.get(identifier)
    if demo is None:
        return None
    if password is not None and not hmac.compare_digest(password, DEMO_PASSWORD):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return demo


def get_current_user(
    authorization: Optional[str] = Header(default=None),
) -> UserContext:
    """
    Extract user context from an active Bearer token. Identity headers are never
    trusted: accepting them would allow a caller to manufacture an ADMIN role.
    """
    # 1. Check Bearer token if provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        session = session_store.get_session(token)
        if session:
            return session.user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authorization token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Bearer authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(min_role: UserRole):
    """Dependency factory enforcing minimum required role level."""
    def dependency(user: UserContext = Depends(get_current_user)) -> UserContext:
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        required_level = ROLE_HIERARCHY.get(min_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Role '{user.role.value}' does not meet required '{min_role.value}' level.",
            )
        return user
    return dependency


def validate_action_permission(user: UserContext, action_type: str) -> None:
    """
    Verify whether the authenticated user has sufficient permissions for the given action.
    """
    if user.role == UserRole.VIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="VIEWER role has read-only access and cannot approve or mutate actions.",
        )

    action_norm = action_type.upper()
    if action_norm in HIGH_IMPACT_ACTIONS:
        if user.role not in (UserRole.SENIOR_ANALYST, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"High-impact action '{action_norm}' requires SENIOR_ANALYST or ADMIN role.",
            )
