"""
In-memory storage backend for testing and development.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from .base import BaseStorage

if TYPE_CHECKING:
    from ..state import MemoryState


class InMemoryStorage(BaseStorage):
    """
    In-memory storage backend.
    
    Data is lost when the process ends. Useful for:
        - Testing
        - Development
        - Short-lived agents
    
    Usage:
        storage = InMemoryStorage()
        state = storage.load_or_create("user_123")
        state.add_session_note("Test note")
        storage.save(state)
    """
    
    def __init__(self):
        self._store: dict[str, dict] = {}
    
    def load(self, user_id: str) -> "MemoryState | None":
        """Load state from memory."""
        from ..state import MemoryState
        
        data = self._store.get(user_id)
        if data is None:
            return None
        
        # Deep copy to prevent accidental mutations
        return MemoryState.from_dict(copy.deepcopy(data))
    
    def save(self, state: "MemoryState") -> None:
        """Save state to memory."""
        # Deep copy to prevent accidental mutations
        self._store[state.user_id] = copy.deepcopy(state.to_dict())
    
    def delete(self, user_id: str) -> bool:
        """Delete state from memory."""
        if user_id in self._store:
            del self._store[user_id]
            return True
        return False
    
    def exists(self, user_id: str) -> bool:
        """Check if state exists in memory."""
        return user_id in self._store
    
    def list_users(self) -> list[str]:
        """List all user IDs."""
        return list(self._store.keys())
    
    def clear(self) -> None:
        """Clear all stored data. Useful for testing."""
        self._store.clear()
    
    def __len__(self) -> int:
        """Number of stored users."""
        return len(self._store)

