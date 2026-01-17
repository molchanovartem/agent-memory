"""
Memory consolidation - merging session memory into global memory.

Uses LLM to:
- Deduplicate semantically similar notes
- Resolve conflicts (recent wins)
- Filter session-specific notes (not durable)
- Remove expired notes
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .state import MemoryState


CONSOLIDATION_PROMPT = """You are a memory consolidation assistant. Your task is to merge session memories into global memories.

## Current Global Memories
{global_notes}

## Session Memories to Process
{session_notes}

## Rules
1. MERGE semantically similar notes (keep the most recent version)
2. RESOLVE conflicts by preferring the most recent information
3. DISCARD session-specific notes that aren't durable (e.g., "this trip only", "just for today")
4. PRESERVE all unique, durable preferences
5. DO NOT invent new information - only use what's in the input
6. Keep notes concise and clear

## Output Format
Return a JSON array of the final consolidated notes. Each note should have:
- "text": The memory content
- "keywords": Array of relevant tags
- "confidence": Confidence score (0.0-1.0)

Example output:
[
    {{"text": "Prefers vegetarian meals when traveling", "keywords": ["dietary"], "confidence": 1.0}},
    {{"text": "Usually prefers aisle seats", "keywords": ["travel", "flight"], "confidence": 0.9}}
]

Return ONLY the JSON array, no other text."""


def _format_notes_for_prompt(notes: list) -> str:
    """Format notes list for the consolidation prompt."""
    if not notes:
        return "(none)"
    
    lines = []
    for note in notes:
        keywords = ", ".join(note.keywords) if note.keywords else "none"
        date = note.last_update.strftime("%Y-%m-%d")
        lines.append(f"- [{keywords}] {note.text} (updated: {date}, confidence: {note.confidence})")
    
    return "\n".join(lines)


async def consolidate_memory(
    state: "MemoryState",
    llm_client: Any,
    model: str = "gpt-4o-mini",
) -> dict:
    """
    Consolidate session memory into global memory using LLM.
    
    Args:
        state: Memory state to consolidate
        llm_client: OpenAI client (or compatible with chat.completions.create)
        model: Model to use
        
    Returns:
        Dict with stats: {"merged": int, "discarded": int, "total": int}
    """
    from .state import MemoryNote
    
    session_notes = list(state.session_memory)
    global_notes = list(state.global_memory)
    
    # Nothing to consolidate
    if not session_notes:
        return {"merged": 0, "discarded": 0, "total": len(global_notes)}
    
    # Build prompt
    prompt = CONSOLIDATION_PROMPT.format(
        global_notes=_format_notes_for_prompt(global_notes),
        session_notes=_format_notes_for_prompt(session_notes),
    )
    
    # Call LLM
    response = await llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Low temperature for consistency
    )
    
    result_text = response.choices[0].message.content.strip()
    
    # Parse result
    try:
        # Handle markdown code blocks
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:-1])
        
        consolidated = json.loads(result_text)
        
        if not isinstance(consolidated, list):
            raise ValueError("Expected JSON array")
            
    except (json.JSONDecodeError, ValueError):
        # Fallback: simple append without deduplication
        consolidated = [
            {"text": n.text, "keywords": n.keywords, "confidence": n.confidence}
            for n in global_notes + session_notes
        ]
    
    # Update global memory
    state.global_memory.clear()
    for item in consolidated:
        state.add_global_note(
            text=item["text"],
            keywords=item.get("keywords", []),
            confidence=item.get("confidence", 1.0),
        )
    
    original_total = len(global_notes) + len(session_notes)
    
    return {
        "merged": original_total - len(consolidated),
        "discarded": len(session_notes) - (len(consolidated) - len(global_notes)),
        "total": len(consolidated),
    }


def consolidate_simple(state: "MemoryState") -> dict:
    """
    Simple consolidation without LLM.
    
    Just appends session notes to global notes.
    Useful for testing or when LLM is not available.
    """
    from .state import MemoryNote
    
    session_notes = list(state.session_memory)
    
    for note in session_notes:
        state.add_global_note(
            text=note.text,
            keywords=note.keywords,
            confidence=note.confidence,
            ttl=note.ttl,
        )
    
    return {
        "merged": 0,
        "discarded": 0,
        "total": len(state.global_memory),
    }

