"""
spine/signal_log.py
Append-only signal log store.
Stores signals emitted by the signal engine for flow tracking and truth assembly.
"""

import json
import os
import sqlite3
from typing import List, Optional

_DB_PATH = os.environ.get("SIGNAL_LOG_PATH", "signal_log.db")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS signal_log (
    sequence_number    INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id           TEXT NOT NULL,
    device_id          TEXT NOT NULL,
    signal_type        TEXT NOT NULL,
    severity           TEXT NOT NULL,
    signal_timestamp   TEXT NOT NULL,
    payload            TEXT NOT NULL
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
    d["payload"] = json.loads(d.get("payload", "{}"))
    return d


def write(signal: dict, db_path: str = None) -> int:
    """Append a signal record. Returns the sequence_number."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO signal_log
                    (trace_id, device_id, signal_type, severity,
                     signal_timestamp, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    signal["trace_id"],
                    signal["device_id"],
                    signal["signal_type"],
                    signal["severity"],
                    signal["signal_timestamp"],
                    json.dumps(signal.get("payload", {})),
                ),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def read_by_device(device_id: str, db_path: str = None) -> List[dict]:
    """Return all signals for a device in ascending sequence order."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM signal_log
            WHERE device_id = ?
            ORDER BY sequence_number ASC
            """,
            (device_id,),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def read_by_trace_id(trace_id: str, db_path: str = None) -> List[dict]:
    """Return all signals with the given trace_id."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM signal_log
            WHERE trace_id = ?
            ORDER BY sequence_number ASC
            """,
            (trace_id,),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def count(db_path: str = None) -> int:
    """Return total number of stored signals."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute("SELECT COUNT(*) FROM signal_log")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def count_up_to_sequence(at_sequence: int, db_path: str = None) -> int:
    """Return count of signals with sequence_number <= at_sequence."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM signal_log WHERE sequence_number <= ?",
            (at_sequence,),
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()


def read_recent_by_device(device_id: str, since_timestamp: str, db_path: str = None) -> List[dict]:
    """Return signals for a device with signal_timestamp >= since_timestamp."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM signal_log
            WHERE device_id = ? AND signal_timestamp >= ?
            ORDER BY sequence_number ASC
            """,
            (device_id, since_timestamp),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
