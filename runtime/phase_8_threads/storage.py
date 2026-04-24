"""
Phase 8: Thread Storage

SQLite-based storage for conversation threads with proper concurrency isolation.
Each thread is completely isolated - no shared memory or state between threads.
"""

import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Thread-local storage to ensure no shared state
_thread_local = threading.local()


@dataclass
class Message:
    """A single message in a conversation thread."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    retrieval_debug_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "retrieval_debug_id": self.retrieval_debug_id
        }


@dataclass
class Thread:
    """
    A conversation thread with complete isolation.
    
    Each thread is identified by a unique UUID and has its own
    isolated message history. No memory or state is shared between
    different threads - they are completely independent.
    
    Attributes:
        thread_id: Unique UUID for this conversation
        session_key: Anonymous session identifier
        created_at: ISO timestamp when thread was created
        updated_at: ISO timestamp of last message
        messages: List of messages (isolated to this thread only)
    """
    thread_id: str
    session_key: str
    created_at: str
    updated_at: str
    messages: List[Message]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "session_key": self.session_key,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages]
        }


class ThreadStorage:
    """
    SQLite storage for conversation threads with proper concurrency isolation.
    
    Each thread operates independently with no shared state:
    - Thread-safe connection pooling
    - Row-level locking via SQLite
    - No in-memory caching between operations
    - Each thread identified by unique UUID
    
    Schema:
    - threads: thread_id, session_key, created_at, updated_at
    - messages: id, thread_id, role, content, timestamp, retrieval_debug_id
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv(
            "THREAD_DB_PATH",
            "data/threads.db"
        )
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Connection pool - one connection per thread
        self._connection_pool: Dict[int, sqlite3.Connection] = {}
        self._pool_lock = threading.Lock()
        
        self._init_db()
        logger.info(f"ThreadStorage initialized: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a thread-specific database connection.
        Each thread gets its own connection - no sharing.
        """
        thread_id = threading.current_thread().ident
        
        with self._pool_lock:
            if thread_id not in self._connection_pool:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
                self._connection_pool[thread_id] = conn
                logger.debug(f"Created new DB connection for thread {thread_id}")
            return self._connection_pool[thread_id]
    
    def _init_db(self):
        """Initialize database tables with WAL mode for better concurrency."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                session_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                retrieval_debug_id TEXT,
                FOREIGN KEY (thread_id) REFERENCES threads(thread_id) ON DELETE CASCADE
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_thread
            ON messages(thread_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_threads_session
            ON threads(session_key)
        """)
        
        conn.commit()
        conn.close()
    
    def create_thread(self, session_key: Optional[str] = None) -> Thread:
        """
        Create a new conversation thread.
        
        Args:
            session_key: Anonymous session identifier (optional)
        
        Returns:
            New Thread object
        """
        thread_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session = session_key or f"anon_{thread_id[:8]}"
        
        conn = self._get_connection()
        with conn:  # Auto-commit/rollback
            conn.execute(
                "INSERT INTO threads (thread_id, session_key, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (thread_id, session, now, now)
            )
        
        logger.info(f"Created thread: {thread_id}")
        
        return Thread(
            thread_id=thread_id,
            session_key=session,
            created_at=now,
            updated_at=now,
            messages=[]
        )
    
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """
        Get a thread by ID with all messages.
        
        Args:
            thread_id: Thread UUID
        
        Returns:
            Thread object or None if not found
        """
        conn = self._get_connection()
        # Get thread
        thread_row = conn.execute(
            "SELECT thread_id, session_key, created_at, updated_at FROM threads WHERE thread_id = ?",
            (thread_id,)
        ).fetchone()
        
        if not thread_row:
            return None
        
        # Get messages
        message_rows = conn.execute(
            "SELECT role, content, timestamp, retrieval_debug_id FROM messages WHERE thread_id = ? ORDER BY id",
            (thread_id,)
        ).fetchall()
        
        messages = [
            Message(
                role=row[0],
                content=row[1],
                timestamp=row[2],
                retrieval_debug_id=row[3]
            )
            for row in message_rows
        ]
        
        return Thread(
            thread_id=thread_row[0],
            session_key=thread_row[1],
            created_at=thread_row[2],
            updated_at=thread_row[3],
            messages=messages
        )
    
    def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        retrieval_debug_id: Optional[str] = None
    ) -> bool:
        """
        Add a message to a thread.
        
        Args:
            thread_id: Thread UUID
            role: 'user' or 'assistant'
            content: Message content
            retrieval_debug_id: Optional retrieval trace ID
        
        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        with conn:  # Transaction
            # Check thread exists
            thread = conn.execute(
                "SELECT 1 FROM threads WHERE thread_id = ?",
                (thread_id,)
            ).fetchone()
            
            if not thread:
                logger.error(f"Thread not found: {thread_id}")
                return False
            
            # Add message
            conn.execute(
                """INSERT INTO messages (thread_id, role, content, timestamp, retrieval_debug_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (thread_id, role, content, now, retrieval_debug_id)
            )
            
            # Update thread timestamp
            conn.execute(
                "UPDATE threads SET updated_at = ? WHERE thread_id = ?",
                (now, thread_id)
            )
        
        logger.debug(f"Added message to thread {thread_id}: {role}")
        return True
    
    def list_threads(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        List all threads with message counts.
        
        Args:
            limit: Maximum threads to return
        
        Returns:
            List of thread summaries
        """
        conn = self._get_connection()
        rows = conn.execute(
            """SELECT t.thread_id, t.session_key, t.created_at, t.updated_at, COUNT(m.id) as msg_count
               FROM threads t
               LEFT JOIN messages m ON t.thread_id = m.thread_id
               GROUP BY t.thread_id
               ORDER BY t.updated_at DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        
        return [
            {
                "thread_id": row[0],
                "session_key": row[1],
                "created_at": row[2],
                "updated_at": row[3],
                "message_count": row[4]
            }
            for row in rows
        ]
    
    def get_recent_messages(
        self,
        thread_id: str,
        n_turns: int = 6
    ) -> List[Message]:
        """
        Get last N turns (user+assistant pairs) from thread.
        
        Args:
            thread_id: Thread UUID
            n_turns: Number of turns (pairs) to retrieve
        
        Returns:
            List of recent messages
        """
        # Each turn = 2 messages (user + assistant)
        limit = n_turns * 2
        
        conn = self._get_connection()
        rows = conn.execute(
            """SELECT role, content, timestamp, retrieval_debug_id
               FROM messages
               WHERE thread_id = ?
               ORDER BY id DESC
               LIMIT ?""",
            (thread_id, limit)
        ).fetchall()
        
        # Reverse to get chronological order
        messages = [
            Message(
                role=row[0],
                content=row[1],
                timestamp=row[2],
                retrieval_debug_id=row[3]
            )
            for row in reversed(rows)
        ]
        
        return messages
    
    def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread and all its messages.
        
        Args:
            thread_id: Thread UUID
        
        Returns:
            True if deleted
        """
        conn = self._get_connection()
        with conn:  # Transaction
            # Delete messages first (foreign key with ON DELETE CASCADE)
            conn.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
            
            # Delete thread
            cursor = conn.execute("DELETE FROM threads WHERE thread_id = ?", (thread_id,))
            
            if cursor.rowcount > 0:
                logger.info(f"Deleted thread: {thread_id}")
                return True
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test storage
    storage = ThreadStorage("data/test_threads.db")
    
    # Create thread
    thread = storage.create_thread("test_session")
    print(f"Created thread: {thread.thread_id}")
    
    # Add messages
    storage.add_message(thread.thread_id, "user", "What is the expense ratio?")
    storage.add_message(thread.thread_id, "assistant", "1.23%", "debug_001")
    
    # Get thread
    loaded = storage.get_thread(thread.thread_id)
    print(f"Loaded thread with {len(loaded.messages)} messages")
    
    # List threads
    threads = storage.list_threads()
    print(f"Listed {len(threads)} threads")
    
    # Cleanup
    storage.delete_thread(thread.thread_id)
    print("Deleted test thread")
