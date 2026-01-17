"""
Memory injection - formats MemoryState for system prompt injection.

Output format:
- Profile as YAML frontmatter
- Global notes as Markdown list with dates
- Session notes with [SESSION] prefix
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .state import MemoryState, MemoryNote


def format_note(note: "MemoryNote", prefix: str = "") -> str:
    """
    Format a single note as a Markdown list item.
    
    Example output:
        - [dietary] Prefers vegetarian meals (confidence: 0.9, updated: 2024-01-15)
    """
    keywords_str = ""
    if note.keywords:
        keywords_str = f"[{', '.join(note.keywords)}] "
    
    date_str = note.last_update.strftime("%Y-%m-%d")
    
    confidence_str = ""
    if note.confidence < 1.0:
        confidence_str = f", confidence: {note.confidence:.1f}"
    
    line = f"- {prefix}{keywords_str}{note.text} (updated: {date_str}{confidence_str})"
    
    return line


def format_notes_section(notes: list["MemoryNote"], header: str, prefix: str = "") -> str:
    """Format a list of notes into a Markdown section."""
    if not notes:
        return ""
    
    lines = [f"## {header}", ""]
    for note in notes:
        lines.append(format_note(note, prefix))
    
    return "\n".join(lines)


def format_profile_yaml(profile: dict) -> str:
    """
    Format profile as YAML frontmatter.
    
    Example output:
        ---
        name: Alice
        loyalty_status: gold
        preferred_language: en
        ---
    """
    if not profile:
        return ""
    
    yaml_content = yaml.dump(profile, default_flow_style=False, allow_unicode=True)
    
    return f"---\n{yaml_content}---"


def to_system_prompt(
    state: "MemoryState",
    include_profile: bool = True,
    include_global: bool = True,
    include_session: bool = True,
    max_notes: int | None = None,
) -> str:
    """
    Convert MemoryState to a formatted string for system prompt injection.
    
    Args:
        state: The memory state to format
        include_profile: Whether to include profile YAML
        include_global: Whether to include global memory notes
        include_session: Whether to include session memory notes
        max_notes: Maximum total notes to include (None = no limit)
    
    Returns:
        Formatted string ready for system prompt injection.
        
    Example output:
        ---
        name: Alice
        loyalty_status: gold
        ---
        
        ## User Memory
        
        - [dietary] Prefers vegetarian meals (updated: 2024-01-15)
        - [travel] Usually prefers aisle seats (updated: 2024-01-10)
        
        ## Current Session
        
        - [SESSION] [flight] Wants window seat this trip for sleeping (updated: 2024-01-20)
    """
    sections = []
    
    # Profile as YAML frontmatter
    if include_profile and state.profile:
        sections.append(format_profile_yaml(state.profile))
    
    # Collect notes with optional limit
    global_notes = list(state.global_memory) if include_global else []
    session_notes = list(state.session_memory) if include_session else []
    
    if max_notes is not None:
        total = len(global_notes) + len(session_notes)
        if total > max_notes:
            # Prioritize session notes, then recent global notes
            session_notes = session_notes[:max_notes]
            remaining = max_notes - len(session_notes)
            # Sort global by recency, take most recent
            global_notes = sorted(global_notes, key=lambda n: n.last_update, reverse=True)[:remaining]
    
    # Global memory section
    global_section = format_notes_section(global_notes, "User Memory")
    if global_section:
        sections.append(global_section)
    
    # Session memory section
    session_section = format_notes_section(session_notes, "Current Session", "[SESSION] ")
    if session_section:
        sections.append(session_section)
    
    return "\n\n".join(sections)


def to_memory_block(state: "MemoryState", **kwargs) -> str:
    """
    Wrap memory in explicit delimiters for safer injection.
    
    Returns memory wrapped in <memory>...</memory> tags.
    """
    content = to_system_prompt(state, **kwargs)
    if not content:
        return ""
    
    return f"<memory>\n{content}\n</memory>"


# Attach method to MemoryState for convenience
def _add_to_system_prompt_method():
    """Monkey-patch to_system_prompt onto MemoryState."""
    from .state import MemoryState
    
    def state_to_system_prompt(self, **kwargs) -> str:
        return to_system_prompt(self, **kwargs)
    
    def state_to_memory_block(self, **kwargs) -> str:
        return to_memory_block(self, **kwargs)
    
    MemoryState.to_system_prompt = state_to_system_prompt
    MemoryState.to_memory_block = state_to_memory_block

