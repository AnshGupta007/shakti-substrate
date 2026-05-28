"""
bhiv/alignment.py
BHIV — Behavioral Integrity Verification module.
Pure function: verify(gov_event, recent_events) -> BhivResult.
No side effects. No I/O. Same inputs → same result.
"""

from dataclasses import dataclass


@dataclass
class BhivResult:
    verdict: str    # "CONSISTENT" | "ANOMALOUS" | "UNVERIFIED"
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "confidence": self.confidence,
            "reason": self.reason,
        }


def verify(gov_event: dict, recent_events: list) -> BhivResult:
    """
    Verify behavioral integrity of a governance event against recent history.
    Checks rules in order: B04 (early exit), B05 (bound violations), B02, B03, B01, then default.
    """

    # BHIV-B04: Insufficient History (early exit)
    if len(recent_events) < 3:
        return BhivResult(
            verdict="UNVERIFIED",
            confidence=0.0,
            reason="Insufficient history for behavioral verification.",
        )

    new_event_type = gov_event.get("event_type", "")
    new_decision = gov_event.get("decision", "")
    new_device_id = gov_event.get("metadata", {}).get("device_id", None)

    # BHIV-B05: Bound Violation Frequency (Task 4)
    # ANOMALOUS with confidence 0.85 if 3+ GOV_BOUND_VIOLATION events in last 10 events
    if new_event_type == "GOV_BOUND_VIOLATION":
        violation_count = sum(
            1 for evt in recent_events if evt.get("event_type") == "GOV_BOUND_VIOLATION"
        )
        if violation_count >= 3:
            return BhivResult(
                verdict="ANOMALOUS",
                confidence=0.85,
                reason="Abnormal bound violation frequency detected.",
            )
        else:
            return BhivResult(
                verdict="CONSISTENT",
                confidence=0.60,
                reason="Bound violation within normal parameters.",
            )

    # BHIV-B02: Suppression Loop Detection
    if new_device_id is not None:
        for evt in recent_events:
            if (evt.get("event_type") == "GOV_POLICY_VIOLATION"
                    and evt.get("metadata", {}).get("device_id") == new_device_id):
                return BhivResult(
                    verdict="ANOMALOUS",
                    confidence=0.90,
                    reason="Device in suppression violation loop.",
                )

    # BHIV-B03: Override Frequency
    override_count = sum(
        1 for evt in recent_events if evt.get("event_type") == "GOV_OVERRIDE"
    )
    if override_count >= 3:
        return BhivResult(
            verdict="ANOMALOUS",
            confidence=0.85,
            reason="Abnormal override frequency detected.",
        )

    # BHIV-B01: Decision Consistency
    same_type_events = [e for e in recent_events if e.get("event_type") == new_event_type]
    if same_type_events:
        same_type_decisions = [e.get("decision") for e in same_type_events]
        all_escalate = all(d == "ESCALATE" for d in same_type_decisions)
        any_escalate = any(d == "ESCALATE" for d in same_type_decisions)

        if len(same_type_events) >= 3:
            if all_escalate and new_decision == "ESCALATE":
                return BhivResult(
                    verdict="CONSISTENT",
                    confidence=0.95,
                    reason="Consistent with repeated escalation pattern for this event type.",
                )
            elif not any_escalate and new_decision == "ESCALATE":
                return BhivResult(
                    verdict="ANOMALOUS",
                    confidence=0.80,
                    reason="ESCALATE decision anomalous: prior events of same type were non-ESCALATE.",
                )
            else:
                return BhivResult(
                    verdict="CONSISTENT",
                    confidence=0.70,
                    reason="Mixed decision history for this event type; decision within norms.",
                )
        else:
            # Fewer than 3 of the same type — mixed baseline
            return BhivResult(
                verdict="CONSISTENT",
                confidence=0.70,
                reason="Insufficient same-type history; assuming consistency.",
            )

    # Default: no specific rule fired
    return BhivResult(
        verdict="CONSISTENT",
        confidence=0.60,
        reason="No anomalous patterns detected.",
    )
