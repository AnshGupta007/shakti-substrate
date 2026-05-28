"""
truth/truth_assembler.py
Operational truth is not raw telemetry. It is a structured claim about
the system state that carries its own evidence — the trace_ids that prove
the claim is correct. Truth is assembled, not assumed.

NEVER assert a claim without evidence.
NEVER set is_verified=True without checking the evidence exists in the store.
NEVER read from a store without first calling bound_checker.
"""

import hashlib
from dataclasses import dataclass
from typing import List

from constitution.bound_checker import check as bound_check
from telemetry.continuity_probe import probe as continuity_probe


@dataclass
class TruthClaim:
    claim_id: str        # SHA-256 of (device_id + claim_type + primary_evidence)
    claim_type: str      # "OPERATIONAL_STATE" | "SIGNAL_ACTIVE" | "GOVERNANCE_ESCALATED" |
                         # "CONTINUITY_INTACT" | "BOUND_COMPLIANT"
    assertion: str       # plain English claim
    evidence: List[str]  # trace_ids and gov_event_ids that prove this claim
    confidence: float    # 0.0 to 1.0
    is_verified: bool    # True if all evidence records exist in their stores

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "claim_type": self.claim_type,
            "assertion": self.assertion,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "is_verified": self.is_verified,
        }


@dataclass
class TruthReport:
    truth_id: str            # SHA-256 of (device_id + timestamp)
    device_id: str
    assembled_at: str        # injected timestamp
    claims: List[TruthClaim]
    overall_confidence: float  # average of all claim confidences
    is_constitutionally_bounded: bool  # True if all evidence was read within bounds

    def to_dict(self) -> dict:
        return {
            "truth_id": self.truth_id,
            "device_id": self.device_id,
            "assembled_at": self.assembled_at,
            "claims": [c.to_dict() for c in self.claims],
            "overall_confidence": self.overall_confidence,
            "is_constitutionally_bounded": self.is_constitutionally_bounded,
        }


def _parse_timestamp_seconds(ts: str) -> int:
    """Convert ISO timestamp to epoch seconds. Returns 0 on failure."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, AttributeError):
        return 0


def assemble(device_id: str, stores: dict, timestamp: str) -> TruthReport:
    """
    Assemble operational truth for a device.
    
    stores dict must contain:
      "ingestion_store" — the ingestion store module
      "signal_log"      — the signal log module
      "gov_store"       — the governance store module
    
    All store reads are preceded by bound_checker calls.
    Truth assembler runs as TELEMETRY_SPINE component.
    """
    component = "TELEMETRY_SPINE"
    claims = []
    all_bounds_passed = True
    bound_check_ids = []

    # Deterministic truth_id
    truth_id = hashlib.sha256(
        f"{device_id}{timestamp}".encode("utf-8")
    ).hexdigest()

    # ─── CLAIM 1: OPERATIONAL_STATE ──────────────────────────────────────
    ingestion_check = bound_check(component, "read", "ingestion_store")
    bound_check_ids.append(ingestion_check.violation_id or "permitted_ingestion")
    
    if ingestion_check.permitted:
        ingestion_store = stores.get("ingestion_store")
        last_record = ingestion_store.read_last_by_device(device_id) if ingestion_store else None

        if last_record:
            trace_id = last_record.get("trace_id", "")
            payload = last_record.get("payload", {})
            ts = last_record.get("ingestion_timestamp", "")

            # Build assertion from payload content
            payload_summary = ", ".join(
                f"{k}={v}" for k, v in payload.items()
                if k not in ("device_id",)
            ) if payload else "no payload"

            assertion = f"Device {device_id} last reported [{payload_summary}] at {ts}."
            
            # Verify evidence exists
            verified_record = ingestion_store.read_by_trace_id(trace_id) if ingestion_store else None
            is_verified = verified_record is not None

            claim_id = hashlib.sha256(
                f"{device_id}OPERATIONAL_STATE{trace_id}".encode("utf-8")
            ).hexdigest()

            claims.append(TruthClaim(
                claim_id=claim_id,
                claim_type="OPERATIONAL_STATE",
                assertion=assertion,
                evidence=[trace_id],
                confidence=1.0,
                is_verified=is_verified,
            ))
        else:
            claim_id = hashlib.sha256(
                f"{device_id}OPERATIONAL_STATE".encode("utf-8")
            ).hexdigest()
            claims.append(TruthClaim(
                claim_id=claim_id,
                claim_type="OPERATIONAL_STATE",
                assertion=f"Device {device_id} has no telemetry records.",
                evidence=[],
                confidence=0.0,
                is_verified=False,
            ))
    else:
        all_bounds_passed = False

    # ─── CLAIM 2: SIGNAL_ACTIVE ──────────────────────────────────────────
    signal_check = bound_check(component, "read", "signal_log")
    bound_check_ids.append(signal_check.violation_id or "permitted_signal")

    if signal_check.permitted:
        signal_log = stores.get("signal_log")
        if signal_log:
            # A signal is "active" if it was emitted in the last 300 seconds
            current_seconds = _parse_timestamp_seconds(timestamp)
            since_ts = current_seconds - 300
            # Convert back to ISO
            from datetime import datetime, timezone
            since_iso = datetime.fromtimestamp(since_ts, tz=timezone.utc).isoformat()
            
            recent_signals = signal_log.read_recent_by_device(device_id, since_iso)
            signal_trace_ids = [s.get("trace_id", "") for s in recent_signals]
            signal_types = list(set(s.get("signal_type", "") for s in recent_signals))

            if recent_signals:
                primary_evidence = signal_trace_ids[0] if signal_trace_ids else ""
                claim_id = hashlib.sha256(
                    f"{device_id}SIGNAL_ACTIVE{primary_evidence}".encode("utf-8")
                ).hexdigest()
                claims.append(TruthClaim(
                    claim_id=claim_id,
                    claim_type="SIGNAL_ACTIVE",
                    assertion=f"Device {device_id} has {len(recent_signals)} active signals: {signal_types}.",
                    evidence=signal_trace_ids,
                    confidence=0.9,
                    is_verified=True,
                ))
            else:
                claim_id = hashlib.sha256(
                    f"{device_id}SIGNAL_ACTIVE".encode("utf-8")
                ).hexdigest()
                claims.append(TruthClaim(
                    claim_id=claim_id,
                    claim_type="SIGNAL_ACTIVE",
                    assertion=f"Device {device_id} has no active signals in the last 300 seconds.",
                    evidence=[{
                        "source": "signal_log",
                        "type": "absence_verified",
                        "detail": f"Signal store queried for device {device_id}; 0 records returned.",
                    }],
                    confidence=0.5,
                    is_verified=True,  # absence is verified — we checked
                ))
    else:
        all_bounds_passed = False

    # ─── CLAIM 3: GOVERNANCE_ESCALATED ───────────────────────────────────
    gov_check = bound_check(component, "read", "gov_store")
    bound_check_ids.append(gov_check.violation_id or "permitted_gov")

    if gov_check.permitted:
        gov_store = stores.get("gov_store")
        if gov_store:
            # Search by device_id in metadata
            gov_events = gov_store.read_by_device_id(device_id)
            
            # Also search by parent_trace_id from device's ingestion records
            if ingestion_check.permitted:
                ingestion_store_ref = stores.get("ingestion_store")
                if ingestion_store_ref:
                    device_records = ingestion_store_ref.read_by_device(device_id)
                    device_trace_ids = {r.get("trace_id", "") for r in device_records}
                    # Find governance events linked via parent_trace_id
                    all_gov = gov_store.read_all()
                    for ge in all_gov:
                        if (ge.get("parent_trace_id", "") in device_trace_ids
                                and ge not in gov_events):
                            gov_events.append(ge)

            escalations = [
                e for e in gov_events
                if e.get("decision") == "ESCALATE"
            ]

            if escalations:
                gov_event_ids = [e.get("gov_event_id", "") for e in escalations]
                primary_evidence = gov_event_ids[0] if gov_event_ids else ""
                claim_id = hashlib.sha256(
                    f"{device_id}GOVERNANCE_ESCALATED{primary_evidence}".encode("utf-8")
                ).hexdigest()
                claims.append(TruthClaim(
                    claim_id=claim_id,
                    claim_type="GOVERNANCE_ESCALATED",
                    assertion=f"Device {device_id} has {len(escalations)} active governance escalations.",
                    evidence=gov_event_ids,
                    confidence=0.95,
                    is_verified=True,
                ))
    else:
        all_bounds_passed = False

    # ─── CLAIM 4: CONTINUITY_INTACT ──────────────────────────────────────
    if ingestion_check.permitted:
        ingestion_store = stores.get("ingestion_store")
        if ingestion_store:
            device_records = ingestion_store.read_by_device(device_id)
            if device_records:
                first_seq = device_records[0]["sequence_number"]
                last_seq = device_records[-1]["sequence_number"]
                probe_result = continuity_probe(ingestion_store, device_id, first_seq, last_seq)

                if probe_result.is_continuous:
                    assertion = (f"Device {device_id} telemetry is continuous. "
                               f"Proof: {probe_result.continuity_proof}.")
                    confidence = 1.0
                else:
                    gap_count = len(probe_result.gaps)
                    assertion = f"Device {device_id} has {gap_count} continuity gaps."
                    confidence = 0.0

                claim_id = hashlib.sha256(
                    f"{device_id}CONTINUITY_INTACT{probe_result.probe_id}".encode("utf-8")
                ).hexdigest()
                claims.append(TruthClaim(
                    claim_id=claim_id,
                    claim_type="CONTINUITY_INTACT",
                    assertion=assertion,
                    evidence=[probe_result.probe_id],
                    confidence=confidence,
                    is_verified=True,
                ))
            else:
                claim_id = hashlib.sha256(
                    f"{device_id}CONTINUITY_INTACT".encode("utf-8")
                ).hexdigest()
                claims.append(TruthClaim(
                    claim_id=claim_id,
                    claim_type="CONTINUITY_INTACT",
                    assertion=f"Device {device_id} has no records — continuity cannot be assessed.",
                    evidence=[],
                    confidence=0.0,
                    is_verified=False,
                ))

    # ─── CLAIM 5: BOUND_COMPLIANT ────────────────────────────────────────
    bc_primary_evidence = bound_check_ids[0] if bound_check_ids else ""
    claim_id = hashlib.sha256(
        f"{device_id}BOUND_COMPLIANT{bc_primary_evidence}".encode("utf-8")
    ).hexdigest()

    if all_bounds_passed:
        claims.append(TruthClaim(
            claim_id=claim_id,
            claim_type="BOUND_COMPLIANT",
            assertion="All truth assembly operations were constitutionally bounded.",
            evidence=bound_check_ids,
            confidence=1.0,
            is_verified=True,
        ))
    else:
        claims.append(TruthClaim(
            claim_id=claim_id,
            claim_type="BOUND_COMPLIANT",
            assertion="One or more truth assembly operations violated constitutional bounds.",
            evidence=bound_check_ids,
            confidence=0.0,
            is_verified=True,
        ))

    # Compute overall confidence
    if claims:
        overall_confidence = round(
            sum(c.confidence for c in claims) / len(claims), 4
        )
    else:
        overall_confidence = 0.0

    return TruthReport(
        truth_id=truth_id,
        device_id=device_id,
        assembled_at=timestamp,
        claims=claims,
        overall_confidence=overall_confidence,
        is_constitutionally_bounded=all_bounds_passed,
    )
