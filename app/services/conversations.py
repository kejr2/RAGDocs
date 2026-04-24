"""
Conversation memory store.

Lives in the same SQLite file as query_logs (query_logs.db) so we don't have
to spin up another connection. Tables:

  conversations(conversation_id PK, created_at, last_active, turn_count, deleted_at)
  conversation_turns(id PK, conversation_id FK, role, content, timestamp, sources_used)

Used by the chat endpoints to persist turns and feed prior context to the
query enhancer for pronoun resolution / follow-up handling.
"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "query_logs.db"

# Hard cap on what we'll ever feed the enhancer (Requirement 4).
ENHANCER_TURN_WINDOW = 3
MAX_LIVE_TURNS = 20


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_conversations_db() -> None:
    """Create tables + idempotent column migrations."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                created_at      TEXT NOT NULL,
                last_active     TEXT NOT NULL,
                turn_count      INTEGER DEFAULT 0,
                deleted_at      TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role            TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content         TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                sources_used    TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_turns_conv "
            "ON conversation_turns(conversation_id, id)"
        )
        conn.commit()
    logger.info("Conversations DB ready at %s", DB_PATH)


def create_conversation() -> str:
    """Insert an empty conversation row and return its id."""
    cid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO conversations (conversation_id, created_at, last_active, turn_count) "
                "VALUES (?, ?, ?, 0)",
                (cid, now, now),
            )
            conn.commit()
    except Exception as e:
        logger.warning("Failed to create conversation: %s", e)
    return cid


def _ensure_conversation(conversation_id: str) -> None:
    """Create the row lazily if a client passes an unknown id."""
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO conversations "
            "(conversation_id, created_at, last_active, turn_count) "
            "VALUES (?, ?, ?, 0)",
            (conversation_id, now, now),
        )
        conn.commit()


def add_turn(
    conversation_id: str,
    role: str,
    content: str,
    sources_used: Optional[List[Dict]] = None,
) -> None:
    """Append a turn and bump the conversation's last_active + turn_count."""
    if role not in ("user", "assistant"):
        raise ValueError(f"invalid role: {role}")
    _ensure_conversation(conversation_id)
    now = datetime.utcnow().isoformat()
    sources_json = json.dumps(sources_used) if sources_used else None
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO conversation_turns "
                "(conversation_id, role, content, timestamp, sources_used) "
                "VALUES (?, ?, ?, ?, ?)",
                (conversation_id, role, content, now, sources_json),
            )
            conn.execute(
                "UPDATE conversations "
                "SET last_active = ?, turn_count = turn_count + 1 "
                "WHERE conversation_id = ?",
                (now, conversation_id),
            )
            conn.commit()
    except Exception as e:
        logger.warning("Failed to add turn: %s", e)


def get_recent_turns(
    conversation_id: str, n: int = ENHANCER_TURN_WINDOW
) -> List[Dict]:
    """
    Return the last *n* turns (chronological order, oldest → newest).
    Excludes the most recent user turn so it can be inserted as the "current"
    query — this is the caller's responsibility, not ours.
    """
    try:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversation_turns "
                "WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, n),
            ).fetchall()
    except Exception as e:
        logger.warning("Failed to fetch turns: %s", e)
        return []
    return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in reversed(rows)]


def get_full_conversation(conversation_id: str) -> Dict:
    """Return conversation metadata + all turns (for /chat/conversation/{id})."""
    try:
        with _conn() as conn:
            meta = conn.execute(
                "SELECT * FROM conversations WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
            if not meta:
                return {}
            rows = conn.execute(
                "SELECT role, content, timestamp, sources_used "
                "FROM conversation_turns WHERE conversation_id = ? ORDER BY id ASC",
                (conversation_id,),
            ).fetchall()
    except Exception as e:
        logger.warning("Failed to fetch conversation: %s", e)
        return {}
    return {
        "conversation_id": meta["conversation_id"],
        "created_at":      meta["created_at"],
        "last_active":     meta["last_active"],
        "turn_count":      meta["turn_count"],
        "deleted_at":      meta["deleted_at"],
        "turns": [
            {
                "role":         r["role"],
                "content":      r["content"],
                "timestamp":    r["timestamp"],
                "sources_used": json.loads(r["sources_used"]) if r["sources_used"] else None,
            }
            for r in rows
        ],
    }


def soft_delete_conversation(conversation_id: str) -> bool:
    """Mark a conversation as deleted but keep turns in the table for logs."""
    now = datetime.utcnow().isoformat()
    try:
        with _conn() as conn:
            cur = conn.execute(
                "UPDATE conversations SET deleted_at = ? WHERE conversation_id = ?",
                (now, conversation_id),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        logger.warning("Failed to soft-delete conversation: %s", e)
        return False
