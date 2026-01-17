"""
State objects for agent memory management.

Core dataclasses: MemoryNote, MemoryNotes, MemoryState.
Based on OpenAI Cookbook's state-based memory pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import uuid


@dataclass
class MemoryNote:
    """
    A single memory note with metadata.
    
    Attributes:
        text: The actual memory content
        keywords: Tags for categorization/filtering
        confidence: How confident we are in this memory (0.0-1.0)
        created_at: When the note was first created
        last_update: When the note was last modified
        ttl: Days until expiry (None = never expires)
        id: Unique identifier
    """
    text: str
    keywords: list[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def is_expired(self) -> bool:
        """Check if this note has expired based on TTL."""
        if self.ttl is None:
            return False
        expiry = self.last_update + timedelta(days=self.ttl)
        return datetime.now() > expiry
    
    def touch(self) -> None:
        """Update last_update timestamp."""
        self.last_update = datetime.now()
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for storage."""
        return {
            "id": self.id,
            "text": self.text,
            "keywords": self.keywords,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_update": self.last_update.isoformat(),
            "ttl": self.ttl,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryNote":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            text=data["text"],
            keywords=data.get("keywords", []),
            confidence=data.get("confidence", 1.0),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            last_update=datetime.fromisoformat(data["last_update"]) if "last_update" in data else datetime.now(),
            ttl=data.get("ttl"),
        )


@dataclass
class MemoryNotes:
    """
    Collection of memory notes with helper methods.
    """
    notes: list[MemoryNote] = field(default_factory=list)
    
    def add(self, note: MemoryNote) -> None:
        """Add a note to the collection."""
        self.notes.append(note)
    
    def remove_expired(self) -> int:
        """Remove expired notes. Returns count of removed notes."""
        original_count = len(self.notes)
        self.notes = [n for n in self.notes if not n.is_expired()]
        return original_count - len(self.notes)
    
    def filter_by_keyword(self, keyword: str) -> list[MemoryNote]:
        """Get notes containing a specific keyword."""
        return [n for n in self.notes if keyword in n.keywords]
    
    def get_by_id(self, note_id: str) -> Optional[MemoryNote]:
        """Find note by ID."""
        for note in self.notes:
            if note.id == note_id:
                return note
        return None
    
    def remove_by_id(self, note_id: str) -> bool:
        """Remove note by ID. Returns True if found and removed."""
        for i, note in enumerate(self.notes):
            if note.id == note_id:
                self.notes.pop(i)
                return True
        return False
    
    def clear(self) -> None:
        """Remove all notes."""
        self.notes = []
    
    def to_list(self) -> list[dict]:
        """Serialize all notes to list of dicts."""
        return [n.to_dict() for n in self.notes]
    
    @classmethod
    def from_list(cls, data: list[dict]) -> "MemoryNotes":
        """Deserialize from list of dicts."""
        notes = [MemoryNote.from_dict(d) for d in data]
        return cls(notes=notes)
    
    def __len__(self) -> int:
        return len(self.notes)
    
    def __iter__(self):
        return iter(self.notes)


@dataclass
class MemoryState:
    """
    Complete memory state for a user.
    
    Contains:
        - profile: Hard facts about the user (name, loyalty status, etc.)
        - global_memory: Persistent preferences that survive across sessions
        - session_memory: Temporary notes for current session only
    
    Usage:
        state = MemoryState(user_id="user_123")
        state.profile["name"] = "Alice"
        state.add_session_note("Prefers vegetarian meals", keywords=["dietary"])
    """
    user_id: str
    profile: dict = field(default_factory=dict)
    global_memory: MemoryNotes = field(default_factory=MemoryNotes)
    session_memory: MemoryNotes = field(default_factory=MemoryNotes)
    
    def add_session_note(
        self,
        text: str,
        keywords: list[str] | None = None,
        confidence: float = 1.0,
        ttl: int | None = None,
    ) -> MemoryNote:
        """
        Add a note to session memory.
        
        Args:
            text: Memory content
            keywords: Tags for categorization
            confidence: Confidence score (0.0-1.0)
            ttl: Days until expiry
            
        Returns:
            The created MemoryNote
        """
        note = MemoryNote(
            text=text,
            keywords=keywords or [],
            confidence=confidence,
            ttl=ttl,
        )
        self.session_memory.add(note)
        return note
    
    def add_global_note(
        self,
        text: str,
        keywords: list[str] | None = None,
        confidence: float = 1.0,
        ttl: int | None = None,
    ) -> MemoryNote:
        """
        Add a note directly to global memory.
        Usually used during consolidation or initial setup.
        """
        note = MemoryNote(
            text=text,
            keywords=keywords or [],
            confidence=confidence,
            ttl=ttl,
        )
        self.global_memory.add(note)
        return note
    
    def clear_session(self) -> None:
        """Clear all session memory. Call after consolidation."""
        self.session_memory.clear()
    
    def cleanup_expired(self) -> dict[str, int]:
        """Remove expired notes from both memories. Returns counts."""
        return {
            "global": self.global_memory.remove_expired(),
            "session": self.session_memory.remove_expired(),
        }
    
    def to_dict(self) -> dict:
        """Serialize full state for storage."""
        return {
            "user_id": self.user_id,
            "profile": self.profile,
            "global_memory": self.global_memory.to_list(),
            "session_memory": self.session_memory.to_list(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryState":
        """Deserialize from storage."""
        return cls(
            user_id=data["user_id"],
            profile=data.get("profile", {}),
            global_memory=MemoryNotes.from_list(data.get("global_memory", [])),
            session_memory=MemoryNotes.from_list(data.get("session_memory", [])),
        )

