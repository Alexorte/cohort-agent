from __future__ import annotations

from typing import Any


class MemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def get(self, session_id: str) -> dict[str, Any]:
        return self._sessions.setdefault(
            session_id,
            {
                "active_cohort_id": None,
                "active_cohort_definition": {},
                "last_user_intent": None,
                "last_chart": None,
                "pending_action": None,
            },
        )

    def update(self, session_id: str, **kwargs: Any) -> dict[str, Any]:
        state = self.get(session_id)
        state.update(kwargs)
        return state