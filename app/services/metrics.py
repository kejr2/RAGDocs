"""
Query metrics logging using a lightweight SQLite database.
Kept separate from the main PostgreSQL DB to avoid schema migration churn.
"""
import sqlite3
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "query_logs.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_metrics_db():
    """Create query_logs table and run idempotent column migrations."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                query_id            TEXT PRIMARY KEY,
                timestamp           TEXT NOT NULL,
                query_text          TEXT NOT NULL,
                chunks_retrieved    INTEGER DEFAULT 0,
                retrieval_score     REAL DEFAULT 0.0,
                retrieval_latency_ms INTEGER DEFAULT 0,
                response_latency_ms INTEGER DEFAULT 0,
                tokens_used         INTEGER DEFAULT 0,
                source_cited        INTEGER DEFAULT 0,
                fallback_triggered  INTEGER DEFAULT 0,
                model_used          TEXT DEFAULT ''
            )
        """)
        conn.commit()

    # Idempotent column migrations
    migrations = [
        "ALTER TABLE query_logs ADD COLUMN feedback INTEGER",
        "ALTER TABLE query_logs ADD COLUMN tokens_in INTEGER DEFAULT 0",
        "ALTER TABLE query_logs ADD COLUMN tokens_out INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            with _conn() as conn:
                conn.execute(sql)
                conn.commit()
        except Exception:
            pass  # Column already exists

    logger.info("Metrics DB ready at %s", DB_PATH)


def log_query(
    *,
    query_text: str,
    chunks_retrieved: int = 0,
    retrieval_score: float = 0.0,
    retrieval_latency_ms: int = 0,
    response_latency_ms: int = 0,
    tokens_used: int = 0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    source_cited: bool = False,
    fallback_triggered: bool = False,
    model_used: str = "",
) -> str:
    """Insert a query log row. Returns the query_id."""
    query_id = str(uuid.uuid4())
    try:
        with _conn() as conn:
            conn.execute(
                """INSERT INTO query_logs
                   (query_id, timestamp, query_text, chunks_retrieved, retrieval_score,
                    retrieval_latency_ms, response_latency_ms, tokens_used,
                    tokens_in, tokens_out,
                    source_cited, fallback_triggered, model_used)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    query_id,
                    datetime.utcnow().isoformat(),
                    query_text[:500],
                    chunks_retrieved,
                    round(retrieval_score, 4),
                    retrieval_latency_ms,
                    response_latency_ms,
                    tokens_used,
                    tokens_in,
                    tokens_out,
                    int(source_cited),
                    int(fallback_triggered),
                    model_used,
                )
            )
            conn.commit()
    except Exception as e:
        logger.warning("Failed to log query metrics: %s", e)
    return query_id


def record_feedback(query_id: str, feedback: int) -> bool:
    """Update the feedback column for a query row. Returns True on success."""
    try:
        with _conn() as conn:
            conn.execute(
                "UPDATE query_logs SET feedback = ? WHERE query_id = ?",
                (feedback, query_id)
            )
            conn.commit()
        return True
    except Exception as e:
        logger.warning("Failed to record feedback: %s", e)
        return False


# Gemini 2.5 Flash pricing (per 1M tokens)
PRICE_PER_M_INPUT  = 0.075   # USD
PRICE_PER_M_OUTPUT = 0.30    # USD


def get_metrics_summary(last_n: int = 50) -> dict:
    """Return aggregated metrics over the last N queries."""
    try:
        with _conn() as conn:
            rows = conn.execute(
                "SELECT * FROM query_logs ORDER BY timestamp DESC LIMIT ?", (last_n,)
            ).fetchall()

        if not rows:
            return {
                "total_queries_served": 0,
                "avg_response_latency_ms": 0,
                "avg_retrieval_score": 0.0,
                "fallback_rate_percent": 0.0,
                "recent_queries": [],
                "feedback_up": 0,
                "feedback_down": 0,
                "feedback_total": 0,
                "helpfulness_percent": 0.0,
                "total_cost_usd": 0.0,
                "avg_cost_per_query_usd": 0.0,
                "total_tokens": 0,
                "unanswered_queries": [],
            }

        total = len(rows)
        avg_latency = sum(r["response_latency_ms"] for r in rows) / total
        avg_score = sum(r["retrieval_score"] for r in rows) / total
        fallback_rate = (sum(r["fallback_triggered"] for r in rows) / total) * 100

        # Feedback stats (feedback column may be NULL)
        def _safe_int(v):
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        feedback_vals = [_safe_int(r["feedback"]) for r in rows]
        feedback_up   = sum(1 for v in feedback_vals if v == 1)
        feedback_down = sum(1 for v in feedback_vals if v == -1)
        feedback_total = feedback_up + feedback_down
        helpfulness_pct = (feedback_up / feedback_total * 100) if feedback_total > 0 else 0.0

        # Cost tracking
        def _safe_tokens(r, col):
            try:
                return int(r[col]) if r[col] is not None else 0
            except (TypeError, ValueError, IndexError):
                return 0

        with _conn() as conn:
            cost_row = conn.execute(
                "SELECT SUM(tokens_in) as ti, SUM(tokens_out) as to_ FROM query_logs"
            ).fetchone()
        total_tokens_in  = int(cost_row["ti"] or 0)
        total_tokens_out = int(cost_row["to_"] or 0)
        total_cost = (
            total_tokens_in  * PRICE_PER_M_INPUT  / 1_000_000 +
            total_tokens_out * PRICE_PER_M_OUTPUT / 1_000_000
        )
        total_count = _total_count()
        avg_cost = total_cost / total_count if total_count > 0 else 0.0

        # Unanswered queries (fallback or very low score)
        with _conn() as conn:
            unanswered_rows = conn.execute(
                """SELECT query_text, timestamp, retrieval_score, chunks_retrieved
                   FROM query_logs
                   WHERE fallback_triggered = 1 OR retrieval_score < 0.5
                   ORDER BY timestamp DESC LIMIT 10"""
            ).fetchall()
        unanswered = [
            {
                "query_text":       r["query_text"],
                "timestamp":        r["timestamp"],
                "retrieval_score":  r["retrieval_score"],
                "chunks_retrieved": r["chunks_retrieved"],
            }
            for r in unanswered_rows
        ]

        recent = [
            {
                "query_id":          r["query_id"],
                "timestamp":         r["timestamp"],
                "query_text":        r["query_text"],
                "chunks_retrieved":  r["chunks_retrieved"],
                "retrieval_score":   r["retrieval_score"],
                "response_latency_ms": r["response_latency_ms"],
                "tokens_used":       r["tokens_used"],
                "source_cited":      bool(r["source_cited"]),
                "fallback_triggered": bool(r["fallback_triggered"]),
                "model_used":        r["model_used"],
                "feedback":          _safe_int(r["feedback"]),
            }
            for r in rows
        ]

        return {
            "total_queries_served":    total_count,
            "avg_response_latency_ms": round(avg_latency),
            "avg_retrieval_score":     round(avg_score, 4),
            "fallback_rate_percent":   round(fallback_rate, 1),
            "recent_queries":          recent,
            "feedback_up":             feedback_up,
            "feedback_down":           feedback_down,
            "feedback_total":          feedback_total,
            "helpfulness_percent":     round(helpfulness_pct, 1),
            "total_cost_usd":          round(total_cost, 6),
            "avg_cost_per_query_usd":  round(avg_cost, 6),
            "total_tokens":            total_tokens_in + total_tokens_out,
            "unanswered_queries":      unanswered,
        }
    except Exception as e:
        logger.warning("Failed to fetch metrics: %s", e)
        return {"error": str(e)}


def _total_count() -> int:
    try:
        with _conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM query_logs").fetchone()[0]
    except Exception:
        return 0
