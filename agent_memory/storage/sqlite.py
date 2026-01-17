"""
SQLite storage backend for persistent memory storage.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from .base import BaseStorage

if TYPE_CHECKING:
    from ..state import MemoryState


class SQLiteStorage(BaseStorage):
    """
    SQLite-based persistent storage backend.
    
    Stores memory state in a SQLite database file.
    
    Usage:
        storage = SQLiteStorage("./memory.db")
        state = storage.load_or_create("user_123")
        storage.save(state)
    
    Schema:
        - memory_states: user_id (PK), data (JSON), updated_at
    """
    
    def __init__(self, db_path: str | Path):
        """
        Initialize SQLite storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_states (
                    user_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for listing users
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_states_updated 
                ON memory_states(updated_at)
            """)
            
            conn.commit()
    
    def load(self, user_id: str) -> "MemoryState | None":
        """Load memory state from database."""
        from ..state import MemoryState
        
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data FROM memory_states WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row is None:
                return None
            
            data = json.loads(row["data"])
            return MemoryState.from_dict(data)
    
    def save(self, state: "MemoryState") -> None:
        """Save memory state to database."""
        data = json.dumps(state.to_dict())
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO memory_states (user_id, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
            """, (state.user_id, data))
            conn.commit()
    
    def delete(self, user_id: str) -> bool:
        """Delete memory state from database."""
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM memory_states WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def exists(self, user_id: str) -> bool:
        """Check if user exists in database."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM memory_states WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            return row is not None
    
    def list_users(self) -> list[str]:
        """List all user IDs in database."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT user_id FROM memory_states ORDER BY updated_at DESC"
            ).fetchall()
            return [row["user_id"] for row in rows]
    
    def vacuum(self) -> None:
        """Optimize database file size."""
        with self._get_conn() as conn:
            conn.execute("VACUUM")
    
    def get_stats(self) -> dict:
        """Get storage statistics."""
        with self._get_conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) as count FROM memory_states"
            ).fetchone()["count"]
            
            size = self.db_path.stat().st_size if self.db_path.exists() else 0
            
            return {
                "user_count": count,
                "db_size_bytes": size,
                "db_path": str(self.db_path),
            }

