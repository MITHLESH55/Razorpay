"""
RiskOrbit — Case Caching & Storage (Phase 2)

Thread-safe in-memory cache for deterministic risk case retrieval.
"""
from __future__ import annotations

import threading
from typing import Optional

from src.investigation.schema import CaseInvestigationResponse


class CaseStorage:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CaseStorage, cls).__new__(cls)
                cls._instance._cases = {}
        return cls._instance

    def save_case(self, case: CaseInvestigationResponse) -> None:
        with self._lock:
            self._cases[case.case_id] = case

    def get_case(self, case_id: str) -> Optional[CaseInvestigationResponse]:
        with self._lock:
            return self._cases.get(case_id)

    def get_case_by_root(self, root_entity_id: str) -> Optional[CaseInvestigationResponse]:
        with self._lock:
            for case in self._cases.values():
                if case.root_entity == root_entity_id:
                    return case
            return None

    def list_cases(self) -> list[CaseInvestigationResponse]:
        with self._lock:
            return list(self._cases.values())

    def clear(self) -> None:
        with self._lock:
            self._cases.clear()
