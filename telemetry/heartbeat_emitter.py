"""
telemetry/heartbeat_emitter.py
Detects devices that have gone silent and emits heartbeat telemetry.
Heartbeat records are REAL records — they enter the store and the
continuity probe counts them.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional


@dataclass
class HeartbeatResult:
    device_id: str
    last_seen_at: Optional[str]       # timestamp of last record, None if never seen
    seconds_since_last: Optional[int]
    heartbeat_emitted: bool
    heartbeat_trace_id: Optional[str]  # trace_id of emitted heartbeat record

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "last_seen_at": self.last_seen_at,
            "seconds_since_last": self.seconds_since_last,
            "heartbeat_emitted": self.heartbeat_emitted,
            "heartbeat_trace_id": self.heartbeat_trace_id,
        }


def _parse_timestamp_seconds(ts: str) -> int:
    """Convert ISO timestamp to epoch seconds. Returns 0 on failure."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return 0


def check_and_emit(
    device_id: str,
    store,
    silence_threshold_seconds: int,
    timestamp: str,
) -> HeartbeatResult:
    """
    Check if a device has gone silent beyond the threshold and emit a heartbeat.
    
    If seconds_since_last > silence_threshold_seconds → emit a synthetic
    telemetry record of source_type="heartbeat".
    
    Heartbeat trace_id: SHA-256 of ("heartbeat" + device_id + timestamp).
    No random(). No datetime.now(). Timestamp is always injected.
    """
    # Read the last record for this device
    last_record = store.read_last_by_device(device_id)

    if last_record is None:
        # Device has never been seen — emit heartbeat
        heartbeat_trace_id = hashlib.sha256(
            f"heartbeat{device_id}{timestamp}".encode("utf-8")
        ).hexdigest()

        heartbeat_record = {
            "trace_id": heartbeat_trace_id,
            "device_id": device_id,
            "source_type": "heartbeat",
            "validation_status": "valid",
            "ingestion_timestamp": timestamp,
            "payload": {
                "device_id": device_id,
                "status": "silent",
                "silence_seconds": None,
            },
        }
        store.write(heartbeat_record)

        return HeartbeatResult(
            device_id=device_id,
            last_seen_at=None,
            seconds_since_last=None,
            heartbeat_emitted=True,
            heartbeat_trace_id=heartbeat_trace_id,
        )

    last_seen_at = last_record.get("ingestion_timestamp", "")
    last_seen_seconds = _parse_timestamp_seconds(last_seen_at)
    current_seconds = _parse_timestamp_seconds(timestamp)
    seconds_since_last = max(0, current_seconds - last_seen_seconds)

    if seconds_since_last > silence_threshold_seconds:
        heartbeat_trace_id = hashlib.sha256(
            f"heartbeat{device_id}{timestamp}".encode("utf-8")
        ).hexdigest()

        heartbeat_record = {
            "trace_id": heartbeat_trace_id,
            "device_id": device_id,
            "source_type": "heartbeat",
            "validation_status": "valid",
            "ingestion_timestamp": timestamp,
            "payload": {
                "device_id": device_id,
                "status": "silent",
                "silence_seconds": seconds_since_last,
            },
        }
        store.write(heartbeat_record)

        return HeartbeatResult(
            device_id=device_id,
            last_seen_at=last_seen_at,
            seconds_since_last=seconds_since_last,
            heartbeat_emitted=True,
            heartbeat_trace_id=heartbeat_trace_id,
        )
    else:
        return HeartbeatResult(
            device_id=device_id,
            last_seen_at=last_seen_at,
            seconds_since_last=seconds_since_last,
            heartbeat_emitted=False,
            heartbeat_trace_id=None,
        )
