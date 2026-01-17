"""
Abstract base class for memory storage backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state import MemoryState


class BaseStorage(ABC):
    """
    Abstract storage interface for memory persistence.
    
    Implementations must provide:
        - load(user_id) -> MemoryState or None
        - save(state) -> None
        - delete(user_id) -> bool
        - exists(user_id) -> bool
        - list_users() -> list of user_ids
    """
    
    @abstractmethod
    def load(self, user_id: str) -> "MemoryState | None":
        """
        Load memory state for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            MemoryState if found, None otherwise
        """
        pass
    
    @abstractmethod
    def save(self, state: "MemoryState") -> None:
        """
        Save memory state.
        
        Args:
            state: The MemoryState to persist
        """
        pass
    
    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """
        Delete all memory for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def exists(self, user_id: str) -> bool:
        """
        Check if memory exists for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            True if exists
        """
        pass
    
    @abstractmethod
    def list_users(self) -> list[str]:
        """
        List all user IDs with stored memory.
        
        Returns:
            List of user_id strings
        """
        pass
    
    def load_or_create(self, user_id: str) -> "MemoryState":
        """
        Load existing state or create new empty one.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            MemoryState (existing or new)
        """
        from ..state import MemoryState
        
        state = self.load(user_id)
        if state is None:
            state = MemoryState(user_id=user_id)
        
        return state

