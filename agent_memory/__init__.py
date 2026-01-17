"""
agent-memory: Long-term memory management for AI agents.

Based on OpenAI Cookbook's state-based memory pattern:
https://cookbook.openai.com/examples/agents_sdk/context_personalization

Core components:
    - MemoryState: User memory state (profile + notes)
    - MemoryNote: Individual memory note
    - MemoryManager: High-level memory operations
    - Storage backends: InMemoryStorage, SQLiteStorage

Quick start:
    from agent_memory import MemoryManager, MemoryState
    from agent_memory.storage import InMemoryStorage
    
    manager = MemoryManager(storage=InMemoryStorage())
    state = manager.load_user("user_123")
    
    # Inject into prompt
    system_prompt = state.to_system_prompt()
    
    # During conversation
    state.add_session_note("User prefers vegetarian meals", keywords=["dietary"])
    
    # After conversation
    await manager.consolidate(state, llm_client)
    manager.save(state)
"""

from .state import MemoryState, MemoryNote, MemoryNotes
from .manager import MemoryManager
from .injection import to_system_prompt, to_memory_block, _add_to_system_prompt_method
from .distillation import create_save_memory_tool, SAVE_MEMORY_TOOL_SCHEMA

# Add convenience methods to MemoryState
_add_to_system_prompt_method()

__version__ = "0.1.0"

__all__ = [
    # Core classes
    "MemoryState",
    "MemoryNote", 
    "MemoryNotes",
    "MemoryManager",
    # Functions
    "to_system_prompt",
    "to_memory_block",
    "create_save_memory_tool",
    # Constants
    "SAVE_MEMORY_TOOL_SCHEMA",
    "__version__",
]

