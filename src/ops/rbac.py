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

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
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

LOCAL_SEED_USERS = [
    {"user_id": "analyst_01", "role": UserRole.ANALYST, "name": "Sarah Chen", "email": "sarah.chen@riskorbit.internal", "title": "Fraud Risk Analyst", "department": "Trust & Safety Operations", "capabilities": ["Queue Triage & Case Search", "Low-Impact Action Approvals (2FA, Delay)", "Analyst Feedback & Ground-Truth Adjudication", "Evidence Graph & Timeline Inspection"]},
    {"user_id": "senior_analyst_01", "role": UserRole.SENIOR_ANALYST, "name": "Marcus Vance", "email": "marcus.vance@riskorbit.internal", "title": "Senior Risk Strategist", "department": "Fraud Policy & Graph Intelligence", "capabilities": ["All Standard Analyst Capabilities", "High-Impact Action Approvals (Block, Restrict, Freeze Ring)", "Policy Decision Overrides & Edit Actions", "Counterfactual Policy Simulation Workbench"]},
    {"user_id": "admin_01", "role": UserRole.ADMIN, "name": "Elena Rostova", "email": "elena.rostova@riskorbit.internal", "title": "Chief Information Security Officer", "department": "Risk Engineering & Governance", "capabilities": ["Complete Enterprise System Access", "Emergency Graph Kill Switch Activation", "Safe Mode Degradation Controls", "Shadow Mode Policy Activation"]},
    {"user_id": "viewer_01", "role": UserRole.VIEWER, "name": "Audit & Compliance Officer", "email": "audit.read@riskorbit.internal", "title": "Independent Regulatory Auditor", "department": "Model Risk & Regulatory Oversight", "capabilities": ["Read-Only Operational Dashboard", "Held-Out Evaluation Metrics Inspection", "Immutable Cryptographic Audit Ledger Access", "Distribution Drift & Stability Verification"]},
]

DEMO_USERS: dict[str, DemoUserRecord] = {
    u["user_id"]: DemoUserRecord(
        user_id=u["user_id"],
        role=u["role"],
        name=u["name"],
        email=u["email"],
        title=u["title"],
        department=u["department"],
        password_hint="Contact your RiskOrbit administrator for access.",
        capabilities=u["capabilities"],
    )
    for u in LOCAL_SEED_USERS
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

PASSWORD_HASH_ITERATIONS = 310000

AUTH_DB_PATH = Path(os.getenv("RISKORBIT_AUTH_DB", "data/processed/riskorbit_users.db"))
GENERIC_AUTH_ERROR = "Invalid user ID/email or password."
MAX_FAILED_LOGINS = int(os.getenv("RISKORBIT_MAX_FAILED_LOGINS", "5"))
LOCKOUT_SECONDS = int(os.getenv("RISKORBIT_LOCKOUT_SECONDS", "900"))


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt_bytes = salt or secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{salt_bytes.hex()}${derived_key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, expected_key_hex = stored_hash.split("$", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(expected_key_hex)
    except (ValueError, TypeError):
        return False
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return hmac.compare_digest(derived_key, expected_key)


class UserRepository:
    def __init__(self, database_path: Path = AUTH_DB_PATH):
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
                    role TEXT NOT NULL, name TEXT NOT NULL, title TEXT,
                    department TEXT, capabilities TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    last_login_at TEXT, failed_login_count INTEGER NOT NULL DEFAULT 0,
                    locked_until REAL, email_verified INTEGER NOT NULL DEFAULT 1
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
                    user_id TEXT, actor_id TEXT, created_at TEXT NOT NULL, details TEXT NOT NULL
                )
            """)
            self._seed(connection)

    def _seed(self, connection: sqlite3.Connection) -> None:
        if os.getenv("RISKORBIT_ENV", "local").lower() in {"production", "prod"}:
            return
        for seed in LOCAL_SEED_USERS:
            seed_password = os.getenv(f"RISKORBIT_SEED_PASSWORD_{seed['user_id'].upper()}")
            if not seed_password:
                continue
            now = datetime.now(timezone.utc).isoformat()
            connection.execute("""
                INSERT OR IGNORE INTO users
                (user_id, username, email, password_hash, role, name, title, department,
                 capabilities, status, created_at, updated_at, email_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, 1)
            """, (seed["user_id"], seed["user_id"], seed["email"].lower(),
                  hash_password(seed_password), seed["role"].value, seed["name"],
                  seed["title"], seed["department"], json.dumps(seed["capabilities"]), now, now))

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        return identifier.strip().lower()

    def find_by_identifier(self, identifier: str) -> Optional[sqlite3.Row]:
        normalized = self._normalize_identifier(identifier)
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?", (normalized, normalized)
            ).fetchone()

    def find_by_id(self, user_id: str) -> Optional[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def record_login_attempt_failure(self, identifier: str) -> None:
        self.record_security_event("LOGIN_FAILED", None, None, {"identifier": self._normalize_identifier(identifier)})

    def list_users(self) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute("SELECT * FROM users ORDER BY username").fetchall()

    def record_login_failure(self, user: sqlite3.Row) -> None:
        count = int(user["failed_login_count"]) + 1
        locked_until = time.time() + LOCKOUT_SECONDS if count >= MAX_FAILED_LOGINS else user["locked_until"]
        with self._connect() as connection:
            connection.execute("UPDATE users SET failed_login_count = ?, locked_until = ?, updated_at = ? WHERE user_id = ?",
                               (count, locked_until, datetime.now(timezone.utc).isoformat(), user["user_id"]))
            self.record_event(connection, "LOGIN_FAILED", user["user_id"], None)

    def record_login_success(self, user_id: str) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE users SET failed_login_count = 0, locked_until = NULL, last_login_at = ?, updated_at = ? WHERE user_id = ?",
                               (datetime.now(timezone.utc).isoformat(), datetime.now(timezone.utc).isoformat(), user_id))
            self.record_event(connection, "LOGIN_SUCCESS", user_id, user_id)

    @staticmethod
    def record_event(connection: sqlite3.Connection, event_type: str, user_id: Optional[str], actor_id: Optional[str], details: Optional[dict] = None) -> None:
        connection.execute("INSERT INTO security_events (event_type, user_id, actor_id, created_at, details) VALUES (?, ?, ?, ?, ?)",
                           (event_type, user_id, actor_id, datetime.now(timezone.utc).isoformat(), json.dumps(details or {})))

    def record_security_event(self, event_type: str, user_id: Optional[str], actor_id: Optional[str], details: Optional[dict] = None) -> None:
        with self._connect() as connection:
            self.record_event(connection, event_type, user_id, actor_id, details)

    def create_user(self, *, username: str, email: str, password: str, role: UserRole, name: str, title: Optional[str] = None, department: Optional[str] = None, capabilities: Optional[list[str]] = None, actor_id: Optional[str] = None) -> sqlite3.Row:
        username = self._normalize_identifier(username)
        email = self._normalize_identifier(email)
        user_id = username
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            try:
                connection.execute("INSERT INTO users (user_id, username, email, password_hash, role, name, title, department, capabilities, status, created_at, updated_at, email_verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, 0)",
                                   (user_id, username, email, hash_password(password), role.value, name.strip(), title, department, json.dumps(capabilities or []), now, now))
            except sqlite3.IntegrityError as exc:
                raise ValueError("User already exists.") from exc
            self.record_event(connection, "USER_CREATED", user_id, actor_id)
        return self.find_by_id(user_id)

    def update_user(self, user_id: str, actor_id: str, *, status_value: Optional[str] = None, role: Optional[UserRole] = None, password: Optional[str] = None) -> Optional[sqlite3.Row]:
        user = self.find_by_id(user_id)
        if user is None:
            return None
        if status_value == "DISABLED" and user["role"] == UserRole.ADMIN.value and len([u for u in self.list_users() if u["role"] == UserRole.ADMIN.value and u["status"] == "ACTIVE"]) <= 1:
            raise ValueError("Cannot disable the last active administrator.")
        fields, values = [], []
        if status_value is not None: fields.extend(["status = ?", "locked_until = NULL"]); values.extend([status_value])
        if role is not None: fields.append("role = ?"); values.append(role.value)
        if password is not None: fields.append("password_hash = ?"); values.append(hash_password(password))
        if not fields: return user
        fields.append("updated_at = ?"); values.append(datetime.now(timezone.utc).isoformat()); values.append(user_id)
        with self._connect() as connection:
            connection.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", values)
            self.record_event(connection, "USER_UPDATED", user_id, actor_id)
        return self.find_by_id(user_id)

    def to_context(self, user: sqlite3.Row) -> UserContext:
        return UserContext(user_id=user["user_id"], role=UserRole(user["role"]), name=user["name"], email=user["email"], title=user["title"], capabilities=json.loads(user["capabilities"]))

    def to_demo_record(self, user: sqlite3.Row) -> DemoUserRecord:
        return DemoUserRecord(user_id=user["user_id"], role=UserRole(user["role"]), name=user["name"], email=user["email"], title=user["title"] or "", department=user["department"] or "", password_hint="Contact your RiskOrbit administrator for access.", capabilities=json.loads(user["capabilities"]))


user_repository = UserRepository()


def _run_password_self_test() -> None:
    test_password = "SelfTest_DynamicSecret_2026!"
    hashed = hash_password(test_password)
    if not verify_password(test_password, hashed):
        raise RuntimeError("PBKDF2 self-test verification failed")
    if verify_password("wrong-password", hashed):
        raise RuntimeError("PBKDF2 self-test wrong-password check failed")


_run_password_self_test()


def authenticate_user(identifier: str, password: str) -> Optional[UserContext]:
    user = user_repository.find_by_identifier(identifier)
    if user is None or user["status"] != "ACTIVE":
        user_repository.record_login_attempt_failure(identifier)
        return None
    if user["locked_until"] and float(user["locked_until"]) > time.time():
        user_repository.record_login_attempt_failure(identifier)
        return None
    if not password or not verify_password(password, user["password_hash"]):
        user_repository.record_login_failure(user)
        return None
    user_repository.record_login_success(user["user_id"])
    return user_repository.to_context(user)


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
            current_user = user_repository.find_by_id(session.user.user_id)
            if current_user is None or current_user["status"] != "ACTIVE":
                session_store.invalidate_session(token)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired authorization token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            session.user = user_repository.to_context(current_user)
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
