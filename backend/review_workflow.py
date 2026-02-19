"""Review workflow utilities for investigator lifecycle."""
from __future__ import annotations

from typing import Dict, List

VALID_STATES = ["DRAFT", "REVIEW", "APPROVED", "SUBMITTED", "REJECTED", "VALIDATION_FAILED"]
TRANSITIONS = {
    "DRAFT": ["REVIEW", "VALIDATION_FAILED"],
    "REVIEW": ["APPROVED", "REJECTED"],
    "APPROVED": ["SUBMITTED"],
    "REJECTED": ["DRAFT"],
    "VALIDATION_FAILED": ["DRAFT"],
}


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, [])


def record_history(history: List[Dict[str, str]] | None, user: str, action: str, comment: str | None) -> List[Dict[str, str]]:
    history = history or []
    history.append({
        "user": user,
        "action": action,
        "comment": comment,
    })
    return history
