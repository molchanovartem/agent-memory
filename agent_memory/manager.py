"""
MemoryManager - main interface for agent memory operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .state import MemoryState
from .storage.base import BaseStorage
from .storage.memory import InMemoryStorage

if TYPE_CHECKING:
    pass


class MemoryManager:
    """
    High-level interface for managing agent memory.
    
    Handles:
        - Loading/saving memory state
        - Session management
        - Memory consolidation
    
    Usage:
        from agent_memory import MemoryManager
        from agent_memory.storage import InMemoryStorage
        
        manager = MemoryManager(storage=InMemoryStorage())
        state = manager.load_user("user_123")
        
        # Work with state...
        state.add_session_note("Prefers vegetarian")
        
        # Consolidate and save
        await manager.consolidate(state, llm_client)
        manager.save(state)
    """
    
    def __init__(self, storage: BaseStorage | None = None):
        """
        Initialize manager with storage backend.
        
        Args:
            storage: Storage backend (defaults to InMemoryStorage)
        """
        self.storage = storage or InMemoryStorage()
    
    def load_user(self, user_id: str) -> MemoryState:
        """
        Load or create memory state for a user.
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            MemoryState for the user
        """
        return self.storage.load_or_create(user_id)
    
    def save(self, state: MemoryState) -> None:
        """
        Save memory state.
        
        Args:
            state: The state to save
        """
        # Clean up expired notes before saving
        state.cleanup_expired()
        self.storage.save(state)
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete all memory for a user.
        
        Args:
            user_id: User to delete
            
        Returns:
            True if deleted
        """
        return self.storage.delete(user_id)
    
    def user_exists(self, user_id: str) -> bool:
        """Check if user has stored memory."""
        return self.storage.exists(user_id)
    
    def list_users(self) -> list[str]:
        """List all users with stored memory."""
        return self.storage.list_users()
    
    async def consolidate(
        self,
        state: MemoryState,
        llm_client: Any,
        model: str = "gpt-4o-mini",
        clear_session: bool = True,
    ) -> dict:
        """
        Consolidate session memory into global memory using LLM.
        
        This merges session notes into global notes, handling:
            - Deduplication of similar notes
            - Conflict resolution (recent wins)
            - Filtering of session-specific notes
        
        Args:
            state: The memory state to consolidate
            llm_client: OpenAI client (or compatible)
            model: Model to use for consolidation
            clear_session: Whether to clear session after consolidation
            
        Returns:
            Dict with consolidation stats
        """
        from .consolidation import consolidate_memory
        
        result = await consolidate_memory(state, llm_client, model=model)
        
        if clear_session:
            state.clear_session()
        
        return result
    
    def consolidate_sync(
        self,
        state: MemoryState,
        llm_client: Any,
        model: str = "gpt-4o-mini",
        clear_session: bool = True,
    ) -> dict:
        """
        Synchronous version of consolidate.
        
        Uses asyncio.run() internally.
        """
        import asyncio
        return asyncio.run(
            self.consolidate(state, llm_client, model=model, clear_session=clear_session)
        )

