"""
observability/replay_safe_observer.py
Provides observability surfaces that are safe to call during replay.
Observer is a PURE FUNCTION over the snapshot. No store reads. No side effects.
Same snapshot + same query → always same result. This is what makes it replay-safe.

After every observe() call, the API layer emits GOV_SURFACE_ACCESS via the
governance router. The observer itself does NOT emit.
"""

import hashlib
from dataclasses import dataclass


@dataclass
class ObservationResult:
    observation_id: str    # SHA-256 of (snapshot_id + query)
    snapshot_id: str       # the snapshot this observation is based on
    query: str
    result: dict           # query-specific result
    is_deterministic: bool # always True — same snapshot + query = same result

    def to_dict(self) -> dict:
        return {
            "observation_id": self.observation_id,
            "snapshot_id": self.snapshot_id,
            "query": self.query,
            "result": self.result,
            "is_deterministic": self.is_deterministic,
        }


def observe(snapshot, query: str) -> ObservationResult:
    """
    Observe the system state captured in a snapshot.
    
    query: "escalations" | "continuity" | "device_status" | "governance_health"
    
    This is a PURE FUNCTION over the snapshot. No store reads. No side effects.
    Same snapshot + same query → always same result.
    The observer does NOT emit GOV_SURFACE_ACCESS — the API layer handles that.
    """
    snapshot_dict = snapshot.to_dict() if hasattr(snapshot, 'to_dict') else snapshot

    snapshot_id = snapshot_dict.get("snapshot_id", "")
    observation_id = hashlib.sha256(
        f"{snapshot_id}{query}".encode("utf-8")
    ).hexdigest()

    if query == "escalations":
        result = {
            "active_escalation_count": len(snapshot_dict.get("active_escalations", [])),
            "escalation_ids": snapshot_dict.get("active_escalations", []),
            "at_sequence": snapshot_dict.get("at_sequence", 0),
        }
    elif query == "continuity":
        result = {
            "continuity_proof": snapshot_dict.get("continuity_proof", ""),
            "ingestion_count": snapshot_dict.get("ingestion_count", 0),
            "at_sequence": snapshot_dict.get("at_sequence", 0),
        }
    elif query == "device_status":
        result = {
            "ingestion_count": snapshot_dict.get("ingestion_count", 0),
            "signal_count": snapshot_dict.get("signal_count", 0),
            "governance_count": snapshot_dict.get("governance_count", 0),
            "taken_at": snapshot_dict.get("taken_at", ""),
        }
    elif query == "governance_health":
        escalation_count = len(snapshot_dict.get("active_escalations", []))
        governance_count = snapshot_dict.get("governance_count", 0)
        escalation_rate = (escalation_count / governance_count) if governance_count > 0 else 0.0
        result = {
            "governance_count": governance_count,
            "escalation_count": escalation_count,
            "escalation_rate": round(escalation_rate, 4),
            "is_replay_safe": snapshot_dict.get("is_replay_safe", False),
        }
    else:
        result = {
            "error": f"Unknown query type: '{query}'",
            "valid_queries": ["escalations", "continuity", "device_status", "governance_health"],
        }

    return ObservationResult(
        observation_id=observation_id,
        snapshot_id=snapshot_id,
        query=query,
        result=result,
        is_deterministic=True,  # always True — pure function
    )
