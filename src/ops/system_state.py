"""
RiskOrbit — Global Operational System State & Controls

Maintains runtime status, degradation toggles, shadow mode, and kill switches.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class SystemHealthStatus(str, Enum):
    """System operational readiness status."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    SAFE_MODE = "SAFE_MODE"
    UNAVAILABLE = "UNAVAILABLE"


class SystemControlsState(BaseModel):
    """System-level operational controls."""
    health_status: SystemHealthStatus = SystemHealthStatus.HEALTHY
    shadow_mode_enabled: bool = Field(
        default=False,
        description="When True: Proposes actions and scores without executing interventions.",
    )
    kill_switch_active: bool = Field(
        default=False,
        description="When True: Automated actions paused; all interventions mandate human approval.",
    )
    graph_engine_available: bool = Field(
        default=True,
        description="Whether graph relationship traversal is currently functional.",
    )
    model_version: str = "riskorbit-risk-v1"
    policy_version: str = "phase3_final_policy"
    active_environment: str = "SYNTHETIC / DEMO"
    last_state_change: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    degradation_reason: Optional[str] = None
    model_ready: bool = False


class SystemStateManager:
    """Thread-safe manager for global system controls."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = SystemControlsState()

    def get_state(self) -> SystemControlsState:
        """Retrieve current system controls state."""
        with self._lock:
            return self._state.model_copy()

    def set_model_ready(self, ready: bool, reason: Optional[str] = None) -> SystemControlsState:
        with self._lock:
            self._state.model_ready = ready
            if not ready:
                self._state.health_status = SystemHealthStatus.UNAVAILABLE
                self._state.degradation_reason = reason or "Required scoring model is unavailable."
            elif self._state.health_status == SystemHealthStatus.UNAVAILABLE:
                self._state.health_status = SystemHealthStatus.HEALTHY
                self._state.degradation_reason = None
            return self._state.model_copy()

    def update_controls(
        self,
        shadow_mode: Optional[bool] = None,
        kill_switch: Optional[bool] = None,
        graph_available: Optional[bool] = None,
        actor_id: str = "admin",
        actor_role: str = "ADMIN",
        reason: Optional[str] = None,
    ) -> SystemControlsState:
        """Update system controls and refresh health status."""
        with self._lock:
            if shadow_mode is not None:
                self._state.shadow_mode_enabled = shadow_mode
            if kill_switch is not None:
                self._state.kill_switch_active = kill_switch
            if graph_available is not None:
                self._state.graph_engine_available = graph_available

            # Compute effective health status
            if not self._state.graph_engine_available:
                self._state.health_status = SystemHealthStatus.DEGRADED
                self._state.degradation_reason = (
                    "Graph engine unavailable — falling back to transaction-level Risk Model."
                )
            elif self._state.kill_switch_active:
                self._state.health_status = SystemHealthStatus.SAFE_MODE
                self._state.degradation_reason = (
                    "Kill Switch active: Automated actions paused — human review only."
                )
            elif self._state.shadow_mode_enabled:
                self._state.health_status = SystemHealthStatus.HEALTHY
                self._state.degradation_reason = "Shadow Mode active — no live interventions executed."
            else:
                self._state.health_status = SystemHealthStatus.HEALTHY
                self._state.degradation_reason = None

            self._state.last_state_change = datetime.now(timezone.utc).isoformat()
            return self._state.model_copy()


# Global singleton instance
system_state = SystemStateManager()
