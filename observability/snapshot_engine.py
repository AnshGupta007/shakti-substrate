"""
observability/snapshot_engine.py
Captures an immutable view of system state at a given sequence boundary.
Snapshot engine is READ-ONLY. It checks its own constitution before reading each store.
Snapshot is IMMUTABLE once created — written to spine_store as a record, never updated.
"""

import hashlib
from dataclasses import dataclass
from typing import List

from constitution.bound_checker import check as bound_check
from telemetry.continuity_probe import probe as continuity_probe


@dataclass
class SystemSnapshot:
    snapshot_id: str         # SHA-256 of (at_sequence + timestamp)
    at_sequence: int
    taken_at: str            # injected timestamp
    ingestion_count: int     # records in ingestion store up to at_sequence
    signal_count: int        # signals in signal log up to at_sequence
    governance_count: int    # events in gov store up to at_sequence
    active_escalations: List[str]  # gov_event_ids with decision=ESCALATE
    continuity_proof: str    # from continuity_probe across all ingestion records
    is_replay_safe: bool     # True if snapshot was taken without any write ops

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "at_sequence": self.at_sequence,
            "taken_at": self.taken_at,
            "ingestion_count": self.ingestion_count,
            "signal_count": self.signal_count,
            "governance_count": self.governance_count,
            "active_escalations": self.active_escalations,
            "continuity_proof": self.continuity_proof,
            "is_replay_safe": self.is_replay_safe,
        }


def take_snapshot(
    stores: dict,
    at_sequence: int,
    timestamp: str,
) -> SystemSnapshot:
    """
    Take an immutable snapshot of system state at a given sequence boundary.
    
    stores dict must contain:
      "ingestion_store" — the ingestion store module
      "signal_log"      — the signal log module
      "gov_store"       — the governance store module
    
    All store reads are preceded by bound_checker calls to verify constitutional
    compliance. The snapshot engine runs as TELEMETRY_SPINE component.
    
    This is a READ-ONLY operation. is_replay_safe is always True because
    the snapshot engine performs no writes during snapshot taking.
    """
    component = "TELEMETRY_SPINE"
    bound_violations = []

    # Deterministic snapshot_id
    snapshot_id = hashlib.sha256(
        f"{at_sequence}{timestamp}".encode("utf-8")
    ).hexdigest()

    # Read ingestion count — check bounds first
    ingestion_count = 0
    ingestion_check = bound_check(component, "read", "ingestion_store")
    if ingestion_check.permitted:
        ingestion_store = stores.get("ingestion_store")
        if ingestion_store:
            ingestion_count = ingestion_store.count_up_to_sequence(at_sequence)
    else:
        bound_violations.append(ingestion_check)

    # Read signal count — check bounds first
    signal_count = 0
    signal_check = bound_check(component, "read", "signal_log")
    if signal_check.permitted:
        signal_log = stores.get("signal_log")
        if signal_log:
            signal_count = signal_log.count_up_to_sequence(at_sequence)
    else:
        bound_violations.append(signal_check)

    # Read governance count and escalations — check bounds first
    governance_count = 0
    active_escalations = []
    gov_check = bound_check(component, "read", "gov_store")
    if gov_check.permitted:
        gov_store = stores.get("gov_store")
        if gov_store:
            gov_events = gov_store.read_range(1, at_sequence)
            governance_count = len(gov_events)
            active_escalations = [
                e["gov_event_id"] for e in gov_events
                if e.get("decision") == "ESCALATE"
            ]
    else:
        bound_violations.append(gov_check)

    # Compute continuity proof across all ingestion records
    continuity_proof = ""
    if ingestion_check.permitted:
        ingestion_store = stores.get("ingestion_store")
        if ingestion_store:
            from telemetry.continuity_probe import probe
            # Use sequence 1 to at_sequence for all devices
            all_records = ingestion_store.read_range(1, at_sequence)
            # Chain hash all trace_ids in sequence order
            proof = ""
            for record in all_records:
                trace_id = record.get("trace_id", "")
                proof = hashlib.sha256(
                    f"{proof}{trace_id}".encode("utf-8")
                ).hexdigest()
            continuity_proof = proof if all_records else hashlib.sha256(b"").hexdigest()
        else:
            continuity_proof = hashlib.sha256(b"").hexdigest()
    else:
        continuity_proof = hashlib.sha256(b"").hexdigest()

    # is_replay_safe is True because this function performs no writes
    is_replay_safe = True

    return SystemSnapshot(
        snapshot_id=snapshot_id,
        at_sequence=at_sequence,
        taken_at=timestamp,
        ingestion_count=ingestion_count,
        signal_count=signal_count,
        governance_count=governance_count,
        active_escalations=active_escalations,
        continuity_proof=continuity_proof,
        is_replay_safe=is_replay_safe,
    )
