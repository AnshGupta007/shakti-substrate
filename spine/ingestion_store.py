"""
spine/ingestion_store.py
Append-only ingestion store for telemetry records.
Used by continuity_probe, flow_tracker, heartbeat_emitter, and truth_assembler.
No updates. No deletes. Sequence numbers assigned by the store.
"""

import json
import os
import sqlite3
from typing import List, Optional

_DB_PATH = os.environ.get("INGESTION_STORE_PATH", "ingestion_store.db")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ingestion_records (
    sequence_number    INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id           TEXT NOT NULL UNIQUE,
    device_id          TEXT NOT NULL,
    source_type        TEXT NOT NULL,
    validation_status  TEXT NOT NULL,
    ingestion_timestamp TEXT NOT NULL,
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


def write(record: dict, db_path: str = None) -> int:
    """Append an ingestion record. Returns the sequence_number."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO ingestion_records
                    (trace_id, device_id, source_type, validation_status,
                     ingestion_timestamp, payload)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record["trace_id"],
                    record["device_id"],
                    record["source_type"],
                    record["validation_status"],
                    record["ingestion_timestamp"],
                    json.dumps(record.get("payload", {})),
                ),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def read_by_device(device_id: str, db_path: str = None) -> List[dict]:
    """Return all records for a device in ascending sequence order."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM ingestion_records
            WHERE device_id = ?
            ORDER BY sequence_number ASC
            """,
            (device_id,),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def read_range(from_seq: int, to_seq: int, db_path: str = None) -> List[dict]:
    """Return records with sequence_number between from_seq and to_seq inclusive."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM ingestion_records
            WHERE sequence_number >= ? AND sequence_number <= ?
            ORDER BY sequence_number ASC
            """,
            (from_seq, to_seq),
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def read_by_trace_id(trace_id: str, db_path: str = None) -> Optional[dict]:
    """Return a single record by trace_id, or None."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT * FROM ingestion_records WHERE trace_id = ?",
            (trace_id,),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def read_last_by_device(device_id: str, db_path: str = None) -> Optional[dict]:
    """Return the most recent record for a device, or None."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            """
            SELECT * FROM ingestion_records
            WHERE device_id = ?
            ORDER BY sequence_number DESC
            LIMIT 1
            """,
            (device_id,),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def count(db_path: str = None) -> int:
    """Return total number of stored ingestion records."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute("SELECT COUNT(*) FROM ingestion_records")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def count_up_to_sequence(at_sequence: int, db_path: str = None) -> int:
    """Return count of records with sequence_number <= at_sequence."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM ingestion_records WHERE sequence_number <= ?",
            (at_sequence,),
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()


def read_all(db_path: str = None) -> List[dict]:
    """Return all records in ascending sequence order."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_table(conn)
        cursor = conn.execute(
            "SELECT * FROM ingestion_records ORDER BY sequence_number ASC"
        )
        return [_row_to_dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
