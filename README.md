# agent-memory

Long-term memory management for AI agents. Based on [OpenAI Cookbook's state-based memory pattern](https://cookbook.openai.com/examples/agents_sdk/context_personalization).

## Features

- **State-based memory**: Profile + notes architecture
- **Session vs Global memory**: Temporary session notes that consolidate into persistent global memory
- **LLM-powered consolidation**: Intelligent deduplication and conflict resolution
- **Multiple storage backends**: In-memory (testing) and SQLite (production)
- **Safety guardrails**: PII blocking, instruction injection prevention, limits

## Installation

```bash
pip install -e .

# With OpenAI support (for consolidation)
pip install -e ".[openai]"
```

## Quick Start

```python
from agent_memory import MemoryManager, MemoryState
from agent_memory.storage import SQLiteStorage

# Initialize
manager = MemoryManager(storage=SQLiteStorage("./memory.db"))
state = manager.load_user("user_123")

# Set profile data
state.profile["name"] = "Alice"
state.profile["loyalty_status"] = "gold"

# Inject into system prompt
system_prompt = state.to_system_prompt()
print(system_prompt)
# ---
# name: Alice
# loyalty_status: gold
# ---
#
# ## User Memory
# - [dietary] Prefers vegetarian meals (updated: 2024-01-15)

# During conversation - capture memories
state.add_session_note(
    text="User prefers vegetarian meals",
    keywords=["dietary"],
    confidence=0.9
)

# After conversation - consolidate session → global
# (requires OpenAI client)
from openai import AsyncOpenAI
client = AsyncOpenAI()
await manager.consolidate(state, client)

# Save
manager.save(state)
```

## Core Concepts

### MemoryState

The central state object containing:
- `profile`: Hard facts (name, loyalty status, preferences)
- `global_memory`: Persistent notes that survive across sessions
- `session_memory`: Temporary notes for current session

### Memory Notes

Individual memory items with metadata:
- `text`: The memory content
- `keywords`: Tags for categorization
- `confidence`: How confident we are (0.0-1.0)
- `ttl`: Days until expiry (optional)

### Injection

Convert state to system prompt format:
- Profile as YAML frontmatter
- Notes as Markdown list
- Session notes marked with `[SESSION]`

### Consolidation

LLM-powered merge of session → global memory:
- Deduplicates similar notes
- Resolves conflicts (recent wins)
- Filters session-specific notes

### Guardrails

Safety checks for memory content:
- Block PII (SSN, credit cards, phone)
- Block instruction-like content
- Enforce limits (max notes, max length)

## Storage Backends

### InMemoryStorage

For testing and development:
```python
from agent_memory.storage import InMemoryStorage
storage = InMemoryStorage()
```

### SQLiteStorage

For production:
```python
from agent_memory.storage import SQLiteStorage
storage = SQLiteStorage("./memory.db")
```

## API Reference

### MemoryManager

```python
manager = MemoryManager(storage=storage)

# Load/create user state
state = manager.load_user("user_123")

# Save state
manager.save(state)

# Delete user
manager.delete_user("user_123")

# Consolidate with LLM
await manager.consolidate(state, llm_client)
```

### MemoryState

```python
state = MemoryState(user_id="user_123")

# Profile
state.profile["name"] = "Alice"

# Add notes
state.add_session_note("Prefers vegetarian", keywords=["dietary"])
state.add_global_note("VIP customer", keywords=["status"])

# Inject to prompt
prompt = state.to_system_prompt()
prompt = state.to_memory_block()  # With <memory> tags

# Cleanup
state.clear_session()
state.cleanup_expired()
```

### Guardrails

```python
from agent_memory.guardrails import (
    GuardrailConfig,
    GuardedMemoryState,
    validate_note_content,
    sanitize_note,
)

# Validate content
result = validate_note_content("User SSN is 123-45-6789")
# result.is_valid = False
# result.violations = ["Contains SSN pattern"]

# Sanitize instead of reject
clean = sanitize_note("Call me at 555-123-4567")
# "Call me at [PHONE REDACTED]"

# Guarded state wrapper
config = GuardrailConfig(max_note_length=200)
guarded = GuardedMemoryState(state, config)
guarded.add_session_note("Safe content")  # Raises on violation
```

## Agent Tool Integration

Use as a tool in your agent:

```python
from agent_memory import create_save_memory_tool, SAVE_MEMORY_TOOL_SCHEMA

# Create tool function bound to state
save_memory = create_save_memory_tool(state)

# Use SAVE_MEMORY_TOOL_SCHEMA for OpenAI function calling
tools = [SAVE_MEMORY_TOOL_SCHEMA]
```

## License

MIT

