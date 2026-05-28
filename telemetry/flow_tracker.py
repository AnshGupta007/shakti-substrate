"""
telemetry/flow_tracker.py
Tracks the journey of a telemetry record through the entire SHAKTI system.
Flow tracker reads ONLY from existing stores. It does NOT write.
It reconstructs the journey by joining records across stores by trace_id.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FlowReport:
    trace_id: str
    flow_stages: List[dict]   # ordered list of stages
    is_complete: bool         # True if record reached the governance layer
    blocked_at: Optional[str] # stage name where record was blocked, if any
    total_duration_ms: int    # from ingestion_timestamp to last stage timestamp

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "flow_stages": self.flow_stages,
            "is_complete": self.is_complete,
            "blocked_at": self.blocked_at,
            "total_duration_ms": self.total_duration_ms,
        }


def _parse_timestamp_ms(ts: str) -> int:
    """Convert ISO timestamp to epoch milliseconds for duration calculation.
    Falls back to 0 if parsing fails."""
    try:
        # Handle ISO format like "2026-05-28T00:00:00"
        from datetime import datetime
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1000)
    except (ValueError, AttributeError):
        return 0


def track(trace_id: str, ingestion_store, signal_log, gov_store) -> FlowReport:
    """
    Track the journey of a telemetry record with the given trace_id through
    all stages of the SHAKTI system.
    
    Stages:
      "ingestion"      — record entered the ingestion store
      "normalisation"  — record was normalised (implicit if ingestion succeeded)
      "signal_eval"    — signal engine evaluated the record
      "governance_emit"— governance events were emitted for this record
      "store_write"    — record was stored in a persistent store
      "surface_access" — record data was accessed via an API surface
    
    This function reads ONLY. It does NOT write anything.
    """
    flow_stages = []
    blocked_at = None
    first_ts_ms = 0
    last_ts_ms = 0

    # Stage 1: Ingestion
    ingestion_record = ingestion_store.read_by_trace_id(trace_id)
    if ingestion_record:
        ts = ingestion_record.get("ingestion_timestamp", "")
        first_ts_ms = _parse_timestamp_ms(ts)
        last_ts_ms = first_ts_ms

        flow_stages.append({
            "stage_name": "ingestion",
            "entered_at": ts,
            "status": "passed",
            "stage_trace": trace_id,
        })

        # Stage 2: Normalisation (implicit if ingestion succeeded)
        flow_stages.append({
            "stage_name": "normalisation",
            "entered_at": ts,
            "status": "passed",
            "stage_trace": trace_id,
        })

        # Check validation status — if rejected, record is blocked at normalisation
        if ingestion_record.get("validation_status") == "rejected":
            flow_stages[-1]["status"] = "blocked"
            blocked_at = "normalisation"
    else:
        # Record not found in ingestion store
        flow_stages.append({
            "stage_name": "ingestion",
            "entered_at": "",
            "status": "skipped",
            "stage_trace": trace_id,
        })
        return FlowReport(
            trace_id=trace_id,
            flow_stages=flow_stages,
            is_complete=False,
            blocked_at="ingestion",
            total_duration_ms=0,
        )

    # Stage 3: Signal Evaluation
    signals = signal_log.read_by_trace_id(trace_id)
    if signals:
        signal_ts = signals[0].get("signal_timestamp", "")
        signal_ts_ms = _parse_timestamp_ms(signal_ts)
        if signal_ts_ms > last_ts_ms:
            last_ts_ms = signal_ts_ms

        flow_stages.append({
            "stage_name": "signal_eval",
            "entered_at": signal_ts,
            "status": "passed",
            "stage_trace": signals[0].get("trace_id", trace_id),
        })
    else:
        flow_stages.append({
            "stage_name": "signal_eval",
            "entered_at": "",
            "status": "skipped",
            "stage_trace": trace_id,
        })

    # If blocked at normalisation, skip remaining stages
    if blocked_at:
        return FlowReport(
            trace_id=trace_id,
            flow_stages=flow_stages,
            is_complete=False,
            blocked_at=blocked_at,
            total_duration_ms=max(0, last_ts_ms - first_ts_ms),
        )

    # Stage 4: Governance Emit
    gov_events = gov_store.read_by_parent_trace_id(trace_id)
    if gov_events:
        gov_ts = gov_events[0].get("governance_timestamp", "")
        gov_ts_ms = _parse_timestamp_ms(gov_ts)
        if gov_ts_ms > last_ts_ms:
            last_ts_ms = gov_ts_ms

        flow_stages.append({
            "stage_name": "governance_emit",
            "entered_at": gov_ts,
            "status": "passed",
            "stage_trace": gov_events[0].get("gov_event_id", ""),
        })
    else:
        flow_stages.append({
            "stage_name": "governance_emit",
            "entered_at": "",
            "status": "skipped",
            "stage_trace": trace_id,
        })

    # Stage 5: Store Write (the ingestion record itself proves store write)
    if ingestion_record:
        flow_stages.append({
            "stage_name": "store_write",
            "entered_at": ingestion_record.get("ingestion_timestamp", ""),
            "status": "passed",
            "stage_trace": trace_id,
        })

    # Stage 6: Surface Access (detected via GOV_SURFACE_ACCESS events)
    surface_events = [e for e in gov_events if e.get("event_type") == "GOV_SURFACE_ACCESS"]
    if surface_events:
        surface_ts = surface_events[0].get("governance_timestamp", "")
        surface_ts_ms = _parse_timestamp_ms(surface_ts)
        if surface_ts_ms > last_ts_ms:
            last_ts_ms = surface_ts_ms

        flow_stages.append({
            "stage_name": "surface_access",
            "entered_at": surface_ts,
            "status": "passed",
            "stage_trace": surface_events[0].get("gov_event_id", ""),
        })
    else:
        flow_stages.append({
            "stage_name": "surface_access",
            "entered_at": "",
            "status": "skipped",
            "stage_trace": trace_id,
        })

    # Determine completion: complete if at least governance_emit stage was passed
    is_complete = any(
        s["stage_name"] == "governance_emit" and s["status"] == "passed"
        for s in flow_stages
    )

    total_duration_ms = max(0, last_ts_ms - first_ts_ms)

    return FlowReport(
        trace_id=trace_id,
        flow_stages=flow_stages,
        is_complete=is_complete,
        blocked_at=blocked_at,
        total_duration_ms=total_duration_ms,
    )
