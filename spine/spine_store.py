"""
spine/spine_store.py
Append-only store for Task 4 records: system snapshots, truth reports,
continuity probes, and flow reports.

Rules:
  → Append-only. No updates. No deletes.
  → SQLite with transactions.
  → Sequence numbers assigned by the store.
  → Survives restart.
"""

import json
import os
import sqlite3
from typing import Optional

_DB_PATH = os.environ.get("SPINE_STORE_PATH", "spine_store.db")

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS snapshots (
    sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id     TEXT NOT NULL UNIQUE,
    data            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS truth_reports (
    sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
    truth_id        TEXT NOT NULL UNIQUE,
    data            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS continuity_probes (
    sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
    probe_id        TEXT NOT NULL,
    data            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS flow_reports (
    sequence_number INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id        TEXT NOT NULL,
    data            TEXT NOT NULL
);
"""


def _get_conn(db_path: str = None) -> sqlite3.Connection:
    path = db_path or _DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(_CREATE_TABLES_SQL)
    conn.commit()


# ─── Snapshots ──────────────────────────────────────────────────────────────

def write_snapshot(snapshot, db_path: str = None) -> int:
    """Write a SystemSnapshot. Returns sequence_number."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_tables(conn)
        data = snapshot.to_dict() if hasattr(snapshot, 'to_dict') else snapshot
        with conn:
            cursor = conn.execute(
                "INSERT INTO snapshots (snapshot_id, data) VALUES (?, ?)",
                (data["snapshot_id"], json.dumps(data)),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def read_latest_snapshot(db_path: str = None) -> Optional[dict]:
    """Return the most recent snapshot, or None."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_tables(conn)
        cursor = conn.execute(
            "SELECT data FROM snapshots ORDER BY sequence_number DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return json.loads(row["data"]) if row else None
    finally:
        conn.close()


def count_snapshots(db_path: str = None) -> int:
    """Return total number of stored snapshots."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_tables(conn)
        cursor = conn.execute("SELECT COUNT(*) FROM snapshots")
        return cursor.fetchone()[0]
    finally:
        conn.close()


# ─── Truth Reports ──────────────────────────────────────────────────────────

def write_truth(truth, db_path: str = None) -> int:
    """Write a TruthReport. Returns sequence_number."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_tables(conn)
        data = truth.to_dict() if hasattr(truth, 'to_dict') else truth
        with conn:
            cursor = conn.execute(
                "INSERT INTO truth_reports (truth_id, data) VALUES (?, ?)",
                (data["truth_id"], json.dumps(data)),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def read_truth_by_id(truth_id: str, db_path: str = None) -> Optional[dict]:
    """Return a TruthReport by truth_id, or None."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_tables(conn)
        cursor = conn.execute(
            "SELECT data FROM truth_reports WHERE truth_id = ?",
            (truth_id,),
        )
        row = cursor.fetchone()
        return json.loads(row["data"]) if row else None
    finally:
        conn.close()


# ─── Continuity Probes ──────────────────────────────────────────────────────

def write_probe(probe, db_path: str = None) -> int:
    """Write a ContinuityResult. Returns sequence_number."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_tables(conn)
        data = probe.to_dict() if hasattr(probe, 'to_dict') else probe
        with conn:
            cursor = conn.execute(
                "INSERT INTO continuity_probes (probe_id, data) VALUES (?, ?)",
                (data["probe_id"], json.dumps(data)),
            )
            return cursor.lastrowid
    finally:
        conn.close()


# ─── Flow Reports ───────────────────────────────────────────────────────────

def write_flow(flow, db_path: str = None) -> int:
    """Write a FlowReport. Returns sequence_number."""
    path = db_path or _DB_PATH
    conn = _get_conn(path)
    try:
        _ensure_tables(conn)
        data = flow.to_dict() if hasattr(flow, 'to_dict') else flow
        with conn:
            cursor = conn.execute(
                "INSERT INTO flow_reports (trace_id, data) VALUES (?, ?)",
                (data["trace_id"], json.dumps(data)),
            )
            return cursor.lastrowid
    finally:
        conn.close()
