"""SQLite persistence layer for sessions, multi-turn state, messages, and turn traces."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from agri_navigator.schemas import (
    MessageRecord,
    SessionCreateResponse,
    SessionDetailResponse,
    TurnTrace,
    utc_now_iso,
)


class SessionNotFoundError(LookupError):
    """Raised when an operation references a non-existent session_id."""


@dataclass(frozen=True)
class SessionState:
    """In-memory snapshot of persisted session state."""

    session_id: str
    created_at: str
    updated_at: str
    active_crop_type: str | None
    pending_clarification: bool
    pending_query: str | None
    turn_count: int


class SQLiteRepository:
    """Transactional, parameterized SQLite data access for conversation state and traces."""

    def __init__(self, db_path: Path, max_history_turns: int = 10) -> None:
        self.db_path = db_path
        self.max_history_turns = max_history_turns
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_schema()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Create required SQLite tables and indexes if absent."""
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active_crop_type TEXT,
                    pending_clarification INTEGER NOT NULL DEFAULT 0,
                    pending_query TEXT,
                    turn_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id, id);

                CREATE TABLE IF NOT EXISTS trace_events (
                    trace_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_number INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_traces_session_id
                ON trace_events(session_id, turn_number);
                """
            )

    def health_check(self) -> bool:
        """Verify SQLite connection and schema availability."""
        try:
            with self._connection() as conn:
                conn.execute("SELECT 1 FROM sessions LIMIT 1;")
            return True
        except sqlite3.Error:
            return False

    def create_session(self) -> SessionCreateResponse:
        """Create and persist a new unique conversation session."""
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, created_at, updated_at,
                    active_crop_type, pending_clarification, pending_query, turn_count
                ) VALUES (?, ?, ?, NULL, 0, NULL, 0);
                """,
                (session_id, now, now),
            )
        return SessionCreateResponse(
            session_id=session_id,
            created_at=now,
            active_crop_type=None,
            pending_clarification=False,
            turn_count=0,
        )

    def get_session_state(self, session_id: str) -> SessionState:
        """Read current persisted state for a session or raise SessionNotFoundError."""
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT session_id, created_at, updated_at,
                       active_crop_type, pending_clarification, pending_query, turn_count
                FROM sessions
                WHERE session_id = ?;
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"Unknown session_id: {session_id}")
        return SessionState(
            session_id=row["session_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            active_crop_type=row["active_crop_type"],
            pending_clarification=bool(row["pending_clarification"]),
            pending_query=row["pending_query"],
            turn_count=int(row["turn_count"]),
        )

    def get_recent_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[MessageRecord]:
        """Fetch bounded recent message history in chronological order."""
        effective_limit = limit or (self.max_history_turns * 2)
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT turn_number, role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?;
                """,
                (session_id, effective_limit),
            ).fetchall()
        records = [
            MessageRecord(
                turn_number=int(r["turn_number"]),
                role=r["role"],
                content=r["content"],
                created_at=r["created_at"],
            )
            for r in reversed(rows)
        ]
        return records

    def get_session_detail(self, session_id: str) -> SessionDetailResponse:
        """Return session state together with bounded recent messages."""
        state = self.get_session_state(session_id)
        messages = self.get_recent_messages(session_id)
        return SessionDetailResponse(
            session_id=state.session_id,
            created_at=state.created_at,
            updated_at=state.updated_at,
            active_crop_type=state.active_crop_type,
            pending_clarification=state.pending_clarification,
            pending_query=state.pending_query,
            turn_count=state.turn_count,
            messages=messages,
        )

    def record_turn(
        self,
        *,
        session_id: str,
        turn_number: int,
        user_message: str,
        assistant_message: str,
        active_crop_type: str | None,
        pending_clarification: bool,
        pending_query: str | None,
        trace: TurnTrace,
    ) -> None:
        """Atomically update session state, append user/assistant messages, and save trace."""
        now = utc_now_iso()
        trace_json = trace.model_dump_json()
        with self._connection() as conn:
            cur = conn.execute(
                """
                UPDATE sessions
                SET updated_at = ?,
                    active_crop_type = ?,
                    pending_clarification = ?,
                    pending_query = ?,
                    turn_count = ?
                WHERE session_id = ?;
                """,
                (
                    now,
                    active_crop_type,
                    int(pending_clarification),
                    pending_query,
                    turn_number,
                    session_id,
                ),
            )
            if cur.rowcount == 0:
                raise SessionNotFoundError(f"Unknown session_id: {session_id}")

            conn.executemany(
                """
                INSERT INTO messages (session_id, turn_number, role, content, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                [
                    (session_id, turn_number, "user", user_message, now),
                    (session_id, turn_number, "assistant", assistant_message, now),
                ],
            )
            conn.execute(
                """
                INSERT INTO trace_events (
                    trace_id, session_id, turn_number, payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?);
                """,
                (trace.trace_id, session_id, turn_number, trace_json, now),
            )

    def get_traces(self, session_id: str) -> list[TurnTrace]:
        """Return chronological trace events for a session."""
        # Ensure session exists first.
        self.get_session_state(session_id)
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM trace_events
                WHERE session_id = ?
                ORDER BY turn_number ASC, created_at ASC;
                """,
                (session_id,),
            ).fetchall()
        return [TurnTrace.model_validate(json.loads(r["payload_json"])) for r in rows]
