"""
Memory distillation - capturing memories during conversation.

Provides tools and helpers for saving memory notes during agent execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .state import MemoryState


def create_save_memory_tool(state: "MemoryState") -> Callable:
    """
    Create a tool function for saving memory notes.
    
    Returns a callable that can be used as an agent tool.
    Compatible with OpenAI function calling format.
    
    Usage:
        save_memory = create_save_memory_tool(state)
        # Use as agent tool
        save_memory(
            text="User prefers vegetarian meals",
            keywords=["dietary"],
            confidence=0.9
        )
    """
    def save_memory_note(
        text: str,
        keywords: list[str] | None = None,
        confidence: float = 1.0,
        ttl: int | None = None,
    ) -> dict:
        """
        Save a memory note to session memory.
        
        Args:
            text: The memory content to save
            keywords: Tags for categorization
            confidence: Confidence score (0.0-1.0)
            ttl: Days until this memory expires (None = never)
            
        Returns:
            Dict with saved note info
        """
        note = state.add_session_note(
            text=text,
            keywords=keywords,
            confidence=confidence,
            ttl=ttl,
        )
        
        return {
            "status": "saved",
            "note_id": note.id,
            "text": note.text,
        }
    
    return save_memory_note


# OpenAI function schema for the save_memory_note tool
SAVE_MEMORY_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_memory_note",
        "description": "Save an important user preference, constraint, or fact to memory for future sessions. Use this when the user shares durable information about themselves.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The memory content to save. Should be a clear, concise statement."
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization (e.g., 'dietary', 'travel', 'work')"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence score. Use lower values for inferred preferences."
                },
                "ttl": {
                    "type": "integer",
                    "description": "Days until expiry. Omit for permanent memories."
                }
            },
            "required": ["text"]
        }
    }
}

