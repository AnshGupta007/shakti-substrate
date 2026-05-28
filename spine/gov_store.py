"""
spine/gov_store.py
Append-only governance event store backed by SQLite.
No updates. No deletes. Sequence numbers assigned by the store.
State survives restarts — SQLite file persisted to disk.
"""

import json
import os
import sqlite3
from typing import Callable, List, Optional

_DB_PATH = os.environ.get("GOV_STORE_PATH", "gov_store.db")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS governance_events (
    sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
    gov_event_id    TEXT NOT NULL UNIQUE,
    event_type      TEXT NOT NULL,
    parent_trace_id TEXT NOT NULL,
    policy_id       TEXT NOT NULL,
    decision        TEXT NOT NULL,
    decision_rationale TEXT NOT NULL,
    bhiv_verdict    TEXT NOT NULL,
    bhiv_confidence REAL NOT NULL,
    tantra_aligned  INTEGER NOT NULL,
    governance_timestamp TEXT NOT NULL,
    metadata        TEXT NOT NULL,
    raw_event       TEXT NOT NULL
);
"""


def _get_conn(db_path: str = None) -> sqlite3.Connection:
    path = db_path or _DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tantra_aligned"] = bool(d["tantra_aligned"])
    # Restore metadata from JSON
    d["metadata"] = json.loads(d.get("metadata", "{}"))
    return d


# ─── Public API ─────────────────────────────────────────────────────────────

def write(gov_event: dict, db_path: str = None) -> int:
    """
    Append a governance event to the store.
    Returns the sequence_number assigned by the store.
    Raises ValueError if gov_event_id already exists (idempotency guard).
    """
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO governance_events
                    (gov_event_id, event_type, parent_trace_id, policy_id,
                     decision, decision_rationale, bhiv_verdict, bhiv_confidence,
                     tantra_aligned, governance_timestamp, metadata, raw_event)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    gov_event["gov_event_id"],
                    gov_event["event_type"],
                    gov_event["parent_trace_id"],
                    gov_event["policy_id"],
                    gov_event["decision"],
                    gov_event["decision_rationale"],
                    gov_event["bhiv_verdict"],
                    gov_event["bhiv_confidence"],
                    1 if gov_event.get("tantra_aligned") else 0,
                    gov_event["governance_timestamp"],
                    json.dumps(gov_event.get("metadata", {})),
                    json.dumps(gov_event),
                ),
            )
            seq_num = cursor.lastrowid
        return seq_num
    finally:
        conn.close()


def read_last_n(n: int, db_path: str = None) -> List[dict]:
    """Return the last n governance events in ascending sequence order."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM governance_events
            ORDER BY sequence_number DESC
            LIMIT ?
            """,
            (n,),
        )
        rows = cursor.fetchall()
        # Reverse so they are in ascending sequence order
        return [_row_to_dict(r) for r in reversed(rows)]
    finally:
        conn.close()


def read_by_id(gov_event_id: str, db_path: str = None) -> Optional[dict]:
    """Return a single governance event by gov_event_id, or None."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT * FROM governance_events WHERE gov_event_id = ?",
            (gov_event_id,),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def replay_all(on_event: Callable[[dict], None], db_path: str = None) -> int:
    """
    Replay all governance events in ascending sequence order.
    Calls on_event(gov_event) for each. Returns total count.
    """
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT * FROM governance_events ORDER BY sequence_number ASC"
        )
        count = 0
        for row in cursor:
            on_event(_row_to_dict(row))
            count += 1
        return count
    finally:
        conn.close()


def read_range(from_seq: int, to_seq: int, db_path: str = None) -> List[dict]:
    """Return all events with sequence_number between from_seq and to_seq inclusive."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM governance_events
            WHERE sequence_number >= ? AND sequence_number <= ?
            ORDER BY sequence_number ASC
            """,
            (from_seq, to_seq),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def count(db_path: str = None) -> int:
    """Return total number of stored governance events."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute("SELECT COUNT(*) FROM governance_events")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def read_by_event_type(event_type: str, limit: int = 100, db_path: str = None) -> List[dict]:
    """Return events of a specific type, newest first, up to limit."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM governance_events
            WHERE event_type = ?
            ORDER BY sequence_number DESC
            LIMIT ?
            """,
            (event_type, limit),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def read_all(db_path: str = None) -> List[dict]:
    """Return all governance events in ascending sequence order."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT * FROM governance_events ORDER BY sequence_number ASC"
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def read_by_parent_trace_id(parent_trace_id: str, db_path: str = None) -> List[dict]:
    """Return all governance events for a given parent_trace_id."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM governance_events
            WHERE parent_trace_id = ?
            ORDER BY sequence_number ASC
            """,
            (parent_trace_id,),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def read_by_device_id(device_id: str, db_path: str = None) -> List[dict]:
    """Return governance events where metadata contains the given device_id."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT * FROM governance_events ORDER BY sequence_number ASC"
        )
        results = []
        for row in cursor:
            d = _row_to_dict(row)
            if d.get("metadata", {}).get("device_id") == device_id:
                results.append(d)
        return results
    finally:
        conn.close()
