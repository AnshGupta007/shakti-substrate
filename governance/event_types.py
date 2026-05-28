"""
governance/event_types.py
All 8 governance event creator functions (7 from Task 3 + GOV_BOUND_VIOLATION).
Each function is a pure function: create_gov_event(parent_trace_id, payload, timestamp) -> dict
gov_event_id is computed as SHA-256 of (event_type + parent_trace_id + policy_id + timestamp)
datetime.now() is NEVER called here — timestamp is always injected externally.
"""

import hashlib

# Canonical governance event types
GOV_EVENT_TYPES = {
    "GOV_POLICY_CHECK",
    "GOV_COMPLIANCE_AUDIT",
    "GOV_TRACE_VERIFY",
    "GOV_SURFACE_ACCESS",
    "GOV_POLICY_VIOLATION",
    "GOV_OVERRIDE",
    "GOV_REPLAY_CONTINUITY",
    "GOV_BOUND_VIOLATION",
}

VALID_DECISIONS = {"ESCALATE", "SUPPRESS", "LOG_ONLY", "BLOCK", "PASS"}


def _compute_gov_event_id(event_type: str, parent_trace_id: str, policy_id: str, timestamp: str) -> str:
    """Deterministic SHA-256 hash from the 4 canonical fields."""
    raw = f"{event_type}{parent_trace_id}{policy_id}{timestamp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _base_event(event_type: str, parent_trace_id: str, policy_id: str,
                timestamp: str, decision: str, decision_rationale: str,
                metadata: dict) -> dict:
    """Build the base governance event dict (without bhiv fields — added by router)."""
    gov_event_id = _compute_gov_event_id(event_type, parent_trace_id, policy_id, timestamp)
    return {
        "gov_event_id": gov_event_id,
        "event_type": event_type,
        "parent_trace_id": parent_trace_id,
        "policy_id": policy_id,
        "decision": decision,
        "decision_rationale": decision_rationale,
        "bhiv_verdict": "UNVERIFIED",      # placeholder — overwritten by router after BHIV runs
        "bhiv_confidence": 0.0,            # placeholder — overwritten by router
        "tantra_aligned": False,           # placeholder — overwritten after TANTRA runs
        "sequence_number": -1,             # placeholder — assigned by gov_store on write
        "governance_timestamp": timestamp,
        "metadata": metadata,
    }


# ─── 1. GOV_POLICY_CHECK ────────────────────────────────────────────────────

def create_gov_policy_check(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered when any SHAKTI signal fires.
    Decision: ESCALATE if severity critical/high, LOG_ONLY if medium, SUPPRESS if low.
    """
    signal_type = payload.get("signal_type", "UNKNOWN")
    severity = payload.get("severity", "low").lower()
    policy_id = payload.get("policy_id", "GOV-OVERLOAD-01")
    policy_version = payload.get("policy_version", "1.0")

    if severity in ("critical", "high"):
        decision = "ESCALATE"
        rationale = f"Signal '{signal_type}' severity='{severity}' requires immediate escalation."
    elif severity == "medium":
        decision = "LOG_ONLY"
        rationale = f"Signal '{signal_type}' severity='{severity}' logged for monitoring."
    else:
        decision = "SUPPRESS"
        rationale = f"Signal '{signal_type}' severity='{severity}' suppressed; below threshold."

    metadata = {
        "signal_type": signal_type,
        "policy_id": policy_id,
        "policy_version": policy_version,
    }
    return _base_event(
        "GOV_POLICY_CHECK", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── 2. GOV_COMPLIANCE_AUDIT ────────────────────────────────────────────────

def create_gov_compliance_audit(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered every 10th consecutive telemetry record per device.
    Decision: PASS if all 10 valid, BLOCK if any rejected.
    """
    device_id = payload.get("device_id", "UNKNOWN")
    region = payload.get("region", "UNKNOWN")
    audit_count = payload.get("audit_count", 1)
    last_audit_gov_event_id = payload.get("last_audit_gov_event_id", "")
    has_rejected = payload.get("has_rejected", False)
    policy_id = "GOV-AUDIT-01"

    if has_rejected:
        decision = "BLOCK"
        rationale = f"Device '{device_id}' had rejected records in last 10 — compliance blocked."
    else:
        decision = "PASS"
        rationale = f"Device '{device_id}' passed compliance audit; all 10 records valid."

    metadata = {
        "device_id": device_id,
        "region": region,
        "audit_count": audit_count,
        "last_audit_gov_event_id": last_audit_gov_event_id,
    }
    return _base_event(
        "GOV_COMPLIANCE_AUDIT", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── 3. GOV_TRACE_VERIFY ────────────────────────────────────────────────────

def create_gov_trace_verify(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered when replay_engine completes a replay run.
    Decision: PASS if divergence_count == 0, ESCALATE otherwise.
    """
    replay_id = payload.get("replay_id", "")
    total_replayed = payload.get("total_replayed", 0)
    divergence_count = payload.get("divergence_count", 0)
    policy_id = "GOV-TRACE-01"

    if divergence_count == 0:
        decision = "PASS"
        rationale = f"Replay '{replay_id}' verified: {total_replayed} events, no divergences."
    else:
        decision = "ESCALATE"
        rationale = (f"Replay '{replay_id}' detected {divergence_count} divergence(s) "
                     f"across {total_replayed} events.")

    metadata = {
        "replay_id": replay_id,
        "total_replayed": total_replayed,
        "divergence_count": divergence_count,
    }
    return _base_event(
        "GOV_TRACE_VERIFY", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── 4. GOV_SURFACE_ACCESS ──────────────────────────────────────────────────

def create_gov_surface_access(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered on every intelligence surface endpoint call.
    Decision: always LOG_ONLY.
    """
    endpoint = payload.get("endpoint", "/unknown")
    method = payload.get("method", "GET")
    caller_id = payload.get("caller_id", "anonymous")
    response_code = payload.get("response_code", 200)
    policy_id = "GOV-ACCESS-01"

    decision = "LOG_ONLY"
    rationale = f"Surface access: {method} {endpoint} by '{caller_id}' → HTTP {response_code}."

    metadata = {
        "endpoint": endpoint,
        "method": method,
        "caller_id": caller_id,
        "response_code": response_code,
    }
    return _base_event(
        "GOV_SURFACE_ACCESS", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── 5. GOV_POLICY_VIOLATION ────────────────────────────────────────────────

def create_gov_policy_violation(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered when a suppressed signal fires again within 60 seconds.
    Decision: always ESCALATE.
    """
    device_id = payload.get("device_id", "UNKNOWN")
    signal_type = payload.get("signal_type", "UNKNOWN")
    previous_gov_event_id = payload.get("previous_gov_event_id", "")
    seconds_since_suppression = payload.get("seconds_since_suppression", 0)
    policy_id = "GOV-VIOLATION-01"

    decision = "ESCALATE"
    rationale = (f"Device '{device_id}' re-triggered '{signal_type}' "
                 f"{seconds_since_suppression}s after suppression.")

    metadata = {
        "device_id": device_id,
        "signal_type": signal_type,
        "previous_gov_event_id": previous_gov_event_id,
        "seconds_since_suppression": seconds_since_suppression,
    }
    return _base_event(
        "GOV_POLICY_VIOLATION", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── 6. GOV_OVERRIDE ────────────────────────────────────────────────────────

def create_gov_override(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered when a human operator overrides an automated governance decision.
    Decision: always LOG_ONLY.
    """
    original_gov_event_id = payload.get("original_gov_event_id", "")
    original_decision = payload.get("original_decision", "UNKNOWN")
    new_decision = payload.get("new_decision", "UNKNOWN")
    operator_id = payload.get("operator_id", "UNKNOWN")
    override_reason = payload.get("override_reason", "")
    policy_id = "GOV-OVERRIDE-01"

    decision = "LOG_ONLY"
    rationale = (f"Operator '{operator_id}' overrode decision '{original_decision}' → "
                 f"'{new_decision}'. Reason: {override_reason}")

    metadata = {
        "original_gov_event_id": original_gov_event_id,
        "original_decision": original_decision,
        "new_decision": new_decision,
        "operator_id": operator_id,
        "override_reason": override_reason,
    }
    return _base_event(
        "GOV_OVERRIDE", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── 7. GOV_REPLAY_CONTINUITY ───────────────────────────────────────────────

def create_gov_replay_continuity(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered when governance event replay is executed.
    Decision: PASS if divergences_detected == 0, ESCALATE otherwise.
    """
    from_sequence = payload.get("from_sequence", 0)
    to_sequence = payload.get("to_sequence", 0)
    governance_events_replayed = payload.get("governance_events_replayed", 0)
    divergences_detected = payload.get("divergences_detected", 0)
    policy_id = "GOV-REPLAY-01"

    if divergences_detected == 0:
        decision = "PASS"
        rationale = (f"Governance replay seq {from_sequence}→{to_sequence}: "
                     f"{governance_events_replayed} events, no divergences.")
    else:
        decision = "ESCALATE"
        rationale = (f"Governance replay seq {from_sequence}→{to_sequence}: "
                     f"{divergences_detected} divergence(s) in {governance_events_replayed} events.")

    metadata = {
        "from_sequence": from_sequence,
        "to_sequence": to_sequence,
        "governance_events_replayed": governance_events_replayed,
        "divergences_detected": divergences_detected,
    }
    return _base_event(
        "GOV_REPLAY_CONTINUITY", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── 8. GOV_BOUND_VIOLATION ─────────────────────────────────────────────────

def create_gov_bound_violation(parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """
    Triggered when bound_checker returns permitted=False for any operation.
    A component attempted an operation outside its declared constitutional authority.
    Decision: always BLOCK — no exceptions.
    """
    component = payload.get("component", "UNKNOWN")
    operation = payload.get("operation", "UNKNOWN")
    target = payload.get("target", "UNKNOWN")
    violation_id = payload.get("violation_id", "")
    policy_id = "GOV-BOUND-01"

    decision = "BLOCK"
    rationale = (f"Constitutional bound violation: component '{component}' attempted "
                 f"'{operation}' on '{target}'. Operation blocked.")

    metadata = {
        "component": component,
        "operation": operation,
        "target": target,
        "violation_id": violation_id,
    }
    return _base_event(
        "GOV_BOUND_VIOLATION", parent_trace_id, policy_id,
        timestamp, decision, rationale, metadata
    )


# ─── DISPATCHER ─────────────────────────────────────────────────────────────

_CREATORS = {
    "GOV_POLICY_CHECK": create_gov_policy_check,
    "GOV_COMPLIANCE_AUDIT": create_gov_compliance_audit,
    "GOV_TRACE_VERIFY": create_gov_trace_verify,
    "GOV_SURFACE_ACCESS": create_gov_surface_access,
    "GOV_POLICY_VIOLATION": create_gov_policy_violation,
    "GOV_OVERRIDE": create_gov_override,
    "GOV_REPLAY_CONTINUITY": create_gov_replay_continuity,
    "GOV_BOUND_VIOLATION": create_gov_bound_violation,
}


def create_gov_event(event_type: str, parent_trace_id: str, payload: dict, timestamp: str) -> dict:
    """Dispatcher: create a governance event of the given type."""
    creator = _CREATORS.get(event_type)
    if creator is None:
        raise ValueError(f"Unknown governance event type: {event_type}")
    return creator(parent_trace_id, payload, timestamp)
